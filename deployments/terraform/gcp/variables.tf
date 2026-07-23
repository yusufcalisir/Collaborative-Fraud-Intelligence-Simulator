variable "gcp_project_id" {
  description = "GCP project ID for all resources"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for all resources"
  type        = string
  default     = "europe-west1"
}

variable "gcp_zone" {
  description = "GCP zone for zonal GKE cluster (empty string = regional cluster)"
  type        = string
  default     = ""
}

variable "gcp_kms_region" {
  description = "GCP region for Cloud KMS KeyRing (must match cluster region)"
  type        = string
  default     = "europe-west1"
}

variable "environment" {
  description = "Deployment environment (production, staging)"
  type        = string
  default     = "production"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "cfi-platform"
}

variable "machine_type" {
  description = "GCE machine type for GKE node pool"
  type        = string
  default     = "n2-standard-8"
}

variable "initial_node_count" {
  description = "Initial number of nodes per zone in the node pool"
  type        = number
  default     = 1
}

variable "min_node_count" {
  description = "Minimum number of nodes in the GKE node pool"
  type        = number
  default     = 2
}

variable "max_node_count" {
  description = "Maximum number of nodes in the GKE node pool"
  type        = number
  default     = 10
}

variable "nodes_subnet_cidr" {
  description = "Primary CIDR range for node subnet"
  type        = string
  default     = "10.2.0.0/24"
}

variable "pods_cidr_range" {
  description = "Secondary CIDR range for pod IPs"
  type        = string
  default     = "10.100.0.0/16"
}

variable "services_cidr_range" {
  description = "Secondary CIDR range for service IPs"
  type        = string
  default     = "10.200.0.0/20"
}

variable "master_ipv4_cidr" {
  description = "CIDR block for GKE control plane private endpoint"
  type        = string
  default     = "172.16.0.0/28"
}

variable "master_authorized_networks" {
  description = "CIDR blocks authorized to access the GKE master endpoint"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = []
}
