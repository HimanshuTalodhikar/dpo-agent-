# ── Terraform Outputs ───��──────────────────────────────────────────────────────

output "ecr_repository_url" {
  description = "ECR repository URL for the CLO MCP container"
  value       = aws_ecr_repository.cloagent.repository_url
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.cloagent.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the ALB for Route53 alias records"
  value       = aws_lb.cloagent.zone_id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.cloagent.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.cloagent.name
}

output "aurora_endpoint" {
  description = "Aurora cluster endpoint"
  value       = aws_rds_cluster.cloagent.endpoint
  sensitive   = true
}

output "aurora_port" {
  description = "Aurora cluster port"
  value       = aws_rds_cluster.cloagent.port
}

output "s3_bucket_name" {
  description = "S3 bucket for legal documents"
  value       = aws_s3_bucket.documents.id
}

output "secrets_manager_secret_arn" {
  description = "Secrets Manager ARN for DB credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "kms_key_arn" {
  description = "KMS key ARN for encryption"
  value       = aws_kms_key.cloagent.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for ECS tasks"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "vpc_id" {
  description = "VPC ID"
  value       = try(aws_vpc.cloagent[0].id, var.existing_vpc_id)
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = compact([for s in aws_subnet.private : s.id])
}
