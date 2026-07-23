output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.cfi.name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API server endpoint"
  value       = aws_eks_cluster.cfi.endpoint
  sensitive   = true
}

output "eks_cluster_certificate_authority" {
  description = "EKS cluster CA certificate data (base64)"
  value       = aws_eks_cluster.cfi.certificate_authority[0].data
  sensitive   = true
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for EKS secrets encryption"
  value       = aws_kms_key.cfi.arn
}

output "kms_key_id" {
  description = "ID of the KMS key"
  value       = aws_kms_key.cfi.key_id
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.cfi.id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "node_security_group_id" {
  description = "Security group ID for EKS node group"
  value       = aws_security_group.eks_nodes.id
}
