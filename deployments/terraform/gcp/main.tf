# =============================================================================
# CFI Platform — GCP Terraform Module
# Provisions: VPC Network, Private Subnet, GKE, Firewall, Cloud KMS KeyRing
# =============================================================================

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# ---------------------------------------------------------------------------
# Locals
# ---------------------------------------------------------------------------
locals {
  common_labels = {
    project     = "cfi-platform"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ---------------------------------------------------------------------------
# VPC Network
# ---------------------------------------------------------------------------
resource "google_compute_network" "cfi" {
  name                    = "${var.cluster_name}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  project                 = var.gcp_project_id
}

resource "google_compute_subnetwork" "cfi_nodes" {
  name                     = "${var.cluster_name}-nodes"
  ip_cidr_range            = var.nodes_subnet_cidr
  region                   = var.gcp_region
  network                  = google_compute_network.cfi.id
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pods_cidr_range
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.services_cidr_range
  }
}

# ---------------------------------------------------------------------------
# Firewall Rules — gRPC mTLS isolation
# ---------------------------------------------------------------------------
resource "google_compute_firewall" "allow_grpc_aggregator" {
  name    = "${var.cluster_name}-allow-grpc-aggregator"
  network = google_compute_network.cfi.id

  description = "Allow gRPC FL Aggregator ingress within VPC"

  allow {
    protocol = "tcp"
    ports    = ["50051", "50052", "8080", "8081"]
  }

  source_ranges = [var.nodes_subnet_cidr]
  target_tags   = ["cfi-node"]
}

resource "google_compute_firewall" "deny_inter_bank" {
  name    = "${var.cluster_name}-deny-inter-bank"
  network = google_compute_network.cfi.id

  description = "Deny direct bank-to-bank gRPC (all traffic must traverse aggregator)"
  priority    = 500

  deny {
    protocol = "tcp"
    ports    = ["50052"]
  }

  source_tags = ["cfi-bank-node"]
  target_tags = ["cfi-bank-node"]
}

resource "google_compute_firewall" "allow_internal" {
  name    = "${var.cluster_name}-allow-internal"
  network = google_compute_network.cfi.id

  description = "Allow Kubernetes internal pod-to-pod communication"

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.pods_cidr_range, var.services_cidr_range]
}

resource "google_compute_firewall" "allow_health_checks" {
  name    = "${var.cluster_name}-allow-health-checks"
  network = google_compute_network.cfi.id

  description = "Allow GCP Load Balancer health check probes"

  allow {
    protocol = "tcp"
    ports    = ["8080", "8081"]
  }

  source_ranges = ["35.191.0.0/16", "130.211.0.0/22"]
}

# ---------------------------------------------------------------------------
# Cloud Router & NAT (private nodes need internet for image pulls)
# ---------------------------------------------------------------------------
resource "google_compute_router" "cfi" {
  name    = "${var.cluster_name}-router"
  region  = var.gcp_region
  network = google_compute_network.cfi.id
}

resource "google_compute_router_nat" "cfi" {
  name                               = "${var.cluster_name}-nat"
  router                             = google_compute_router.cfi.name
  region                             = var.gcp_region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"

  subnetwork {
    name                    = google_compute_subnetwork.cfi_nodes.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
}

# ---------------------------------------------------------------------------
# GKE Cluster
# ---------------------------------------------------------------------------
resource "google_container_cluster" "cfi" {
  provider = google-beta

  name     = var.cluster_name
  location = var.gcp_zone != "" ? var.gcp_zone : var.gcp_region
  project  = var.gcp_project_id

  # Use separately managed node pools
  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.cfi.id
  subnetwork = google_compute_subnetwork.cfi_nodes.id

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = var.master_ipv4_cidr
  }

  master_authorized_networks_config {
    dynamic "cidr_blocks" {
      for_each = var.master_authorized_networks
      content {
        cidr_block   = cidr_blocks.value.cidr_block
        display_name = cidr_blocks.value.display_name
      }
    }
  }

  # Secrets encrypted with Cloud KMS CMEK
  database_encryption {
    state    = "ENCRYPTED"
    key_name = google_kms_crypto_key.cfi.id
  }

  workload_identity_config {
    workload_pool = "${var.gcp_project_id}.svc.id.goog"
  }

  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
  }

  release_channel {
    channel = "STABLE"
  }

  logging_service    = "logging.googleapis.com/kubernetes"
  monitoring_service = "monitoring.googleapis.com/kubernetes"

  depends_on = [google_kms_crypto_key.cfi]
}

resource "google_container_node_pool" "cfi_nodes" {
  provider = google-beta

  name       = "${var.cluster_name}-nodes"
  location   = google_container_cluster.cfi.location
  cluster    = google_container_cluster.cfi.name
  project    = var.gcp_project_id

  initial_node_count = var.initial_node_count

  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = var.machine_type
    disk_size_gb = 100
    disk_type    = "pd-ssd"
    image_type   = "COS_CONTAINERD"

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    labels = local.common_labels
    tags   = ["cfi-node"]
  }
}

# ---------------------------------------------------------------------------
# Cloud KMS — KeyRing & CryptoKey
# ---------------------------------------------------------------------------
resource "google_kms_key_ring" "cfi" {
  name     = "${var.cluster_name}-keyring"
  location = var.gcp_kms_region
  project  = var.gcp_project_id
}

resource "google_kms_crypto_key" "cfi" {
  name            = "${var.cluster_name}-key"
  key_ring        = google_kms_key_ring.cfi.id
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}
