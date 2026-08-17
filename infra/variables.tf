# ── Terraform Variables ────���───────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["local", "staging", "production"], var.environment)
    error_message = "Environment must be local, staging, or production."
  }
}

variable "existing_vpc_id" {
  description = "Use an existing VPC ID instead of creating a new one (optional)"
  type        = string
  default     = ""
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8000
}

variable "desired_count" {
  description = "Number of ECS task instances"
  type        = number
  default     = 2
}

variable "memory" {
  description = "Container memory in MB"
  type        = number
  default     = 2048
}

variable "cpu" {
  description = "Container CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for LLM"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v1"
}

variable "embedding_model_id" {
  description = "Bedrock embedding model ID"
  type        = string
  default     = "amazon.titan-embed-text-v2"
}

variable "embedding_dimensions" {
  description = "Embedding vector dimensions"
  type        = number
  default     = 1024
}

variable "aurora_serverless_v2_min_capacity" {
  description = "Aurora Serverless v2 minimum ACU"
  type        = number
  default     = 0.5
}

variable "aurora_serverless_v2_max_capacity" {
  description = "Aurora Serverless v2 maximum ACU"
  type        = number
  default     = 16
}

variable "db_name" {
  description = "Aurora database name"
  type        = string
  default     = "cloagent"
}

variable "db_username" {
  description = "Aurora master username (stored in Secrets Manager)"
  type        = string
  default     = "cloagent_admin"
}

variable "s3_bucket_name" {
  description = "S3 bucket for legal documents"
  type        = string
  default     = "cloagent-documents"
}

variable "ecr_repository_name" {
  description = "ECR repository name"
  type        = string
  default     = "cloagent"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "enable_patrol_deletion_protection" {
  description = "Enable deletion protection for RDS and ECS"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the ALB (empty = any)"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
variable "domain_name" {
  description = "Domain name for HTTPS cert + Route53 alias (e.g. cloagent.example.com). Leave empty to skip TLS."
  type        = string
  default     = ""
}
