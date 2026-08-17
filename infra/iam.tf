# ─�� IAM: Roles and Policies ──────────────────────────────────────────────────────

# Additional IAM resources are defined inline in ecs.tf (task role, execution role)
# This file contains any additional IAM resources needed

# ECS Cluster autoscaling role (for future scaling)
resource "aws_iam_role" "ecs_autoscaling" {
  name = "${local.app_name}-ecs-autoscaling-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

# ECR Repository
resource "aws_ecr_repository" "cloagent" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

# ECR lifecycle policy: keep last 10 images
resource "aws_ecr_lifecycle_policy" "cloagent" {
  repository = aws_ecr_repository.cloagent.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
