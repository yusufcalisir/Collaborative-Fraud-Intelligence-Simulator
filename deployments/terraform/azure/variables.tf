variable "azure_location" {
  description = "Azure region for all resources"
  type        = string
  default     = "westeurope"
}

variable "environment" {
  description = "Deployment environment (production, staging)"
  type        = string
  default     = "production"
}

variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = "cfi-platform-rg"
}

variable "cluster_name" {
  description = "AKS cluster name"
  type        = string
  default     = "cfi-platform"
}

variable "kubernetes_version" {
  description = "Kubernetes version for AKS cluster"
  type        = string
  default     = "1.30"
}

variable "vnet_address_space" {
  description = "Address space for the Virtual Network"
  type        = string
  default     = "10.1.0.0/16"
}

variable "aks_subnet_cidr" {
  description = "CIDR for AKS node subnet"
  type        = string
  default     = "10.1.1.0/24"
}

variable "private_endpoint_subnet_cidr" {
  description = "CIDR for private endpoint subnet"
  type        = string
  default     = "10.1.2.0/24"
}

variable "node_vm_size" {
  description = "VM size for the default AKS system node pool"
  type        = string
  default     = "Standard_D8s_v4"
}

variable "system_node_count" {
  description = "Number of nodes in the system node pool"
  type        = number
  default     = 3
}

variable "bank_node_vm_size" {
  description = "VM size for bank client node pool"
  type        = string
  default     = "Standard_D4s_v4"
}

variable "bank_node_count" {
  description = "Initial number of bank client nodes"
  type        = number
  default     = 3
}

variable "bank_node_min_count" {
  description = "Minimum bank client node pool size"
  type        = number
  default     = 2
}

variable "bank_node_max_count" {
  description = "Maximum bank client node pool size"
  type        = number
  default     = 10
}

variable "key_vault_allowed_ips" {
  description = "Allowed IP ranges for Azure Key Vault network ACL"
  type        = list(string)
  default     = []
}
