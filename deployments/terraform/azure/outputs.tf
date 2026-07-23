output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.cfi.name
}

output "aks_cluster_endpoint" {
  description = "AKS cluster API server endpoint"
  value       = azurerm_kubernetes_cluster.cfi.kube_config[0].host
  sensitive   = true
}

output "aks_cluster_client_certificate" {
  description = "AKS cluster client certificate (base64)"
  value       = azurerm_kubernetes_cluster.cfi.kube_config[0].client_certificate
  sensitive   = true
}

output "aks_kube_config_raw" {
  description = "Raw kubeconfig for AKS cluster"
  value       = azurerm_kubernetes_cluster.cfi.kube_config_raw
  sensitive   = true
}

output "key_vault_id" {
  description = "Azure Key Vault resource ID"
  value       = azurerm_key_vault.cfi.id
}

output "key_vault_uri" {
  description = "Azure Key Vault URI"
  value       = azurerm_key_vault.cfi.vault_uri
}

output "resource_group_name" {
  description = "Azure resource group name"
  value       = azurerm_resource_group.cfi.name
}

output "vnet_id" {
  description = "Virtual Network resource ID"
  value       = azurerm_virtual_network.cfi.id
}

output "aks_nodes_subnet_id" {
  description = "AKS node subnet resource ID"
  value       = azurerm_subnet.aks_nodes.id
}

output "nsg_id" {
  description = "Network Security Group resource ID"
  value       = azurerm_network_security_group.cfi.id
}
