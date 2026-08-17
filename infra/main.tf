# ── Terraform Configuration for CLO MCP Platform ─────────────────────���────────
# Phase 1: ECS/Fargate + Aurora Serverless v2 + S3 + Bedrock
# ───────────────────��─────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state in S3 + DynamoDB (create the bucket manually for state first)
  backend "s3" {
    bucket         = "cloagent-terraform-state-430896782648"
    key            = "infra/main.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "cloagent-terraform-locks"
  }
}

# ── Provider ───────────────────────────────────────────────────────────────────

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "cloagent"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── Locals ────────────��───────────────────────────────────────────────────────

locals {
  app_name    = "cloagent"
  environment = var.environment
  vpc_cidr    = "10.0.0.0/16"
}

# ── Data sources ──────────────────────────────────────────────────────────────

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_vpc" "existing" {
  count = var.existing_vpc_id != "" ? 1 : 0
  id    = var.existing_vpc_id
}

# Required: list available AZs in the current region
data "aws_availability_zones" "available" {
  state = "available"
}
