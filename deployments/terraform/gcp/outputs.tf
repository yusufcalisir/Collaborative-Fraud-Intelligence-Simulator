output "gke_cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.cfi.name
}

output "gke_cluster_endpoint" {
  description = "GKE cluster API server endpoint"
  value       = google_container_cluster.cfi.endpoint
  sensitive   = true
}

output "gke_cluster_ca_certificate" {
  description = "GKE cluster CA certificate (base64)"
  value       = google_container_cluster.cfi.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "kms_keyring_id" {
  description = "Cloud KMS KeyRing resource ID"
  value       = google_kms_key_ring.cfi.id
}

output "kms_key_id" {
  description = "Cloud KMS CryptoKey resource ID"
  value       = google_kms_crypto_key.cfi.id
}

output "vpc_network_name" {
  description = "VPC network name"
  value       = google_compute_network.cfi.name
}

output "vpc_network_id" {
  description = "VPC network self-link"
  value       = google_compute_network.cfi.id
}

output "nodes_subnet_name" {
  description = "GKE node subnet name"
  value       = google_compute_subnetwork.cfi_nodes.name
}

output "workload_identity_pool" {
  description = "Workload Identity pool for GKE workloads"
  value       = "${var.gcp_project_id}.svc.id.goog"
}
