# ── ECS Fargate Service ───���────────────────────────────────────────────────────
# ── ECS Service IAM Role ───────────────────────────────────────────────────────
# Required: ECS service needs this role to register/deregister with the ALB.

resource "aws_iam_role" "ecs_service" {
  name = "${local.app_name}-ecs-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

# Inline policy: what AmazonECSServiceRolePolicy grants (ALB registration)
resource "aws_iam_policy" "ecs_service" {
  name = "${local.app_name}-ecs-service-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "elasticloadbalancing:RegisterTargets",
          "elasticloadbalancing:DeregisterTargets",
          "elasticloadbalancing:Describe*",
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecs_service" {
  role       = aws_iam_role.ecs_service.name
  policy_arn = aws_iam_policy.ecs_service.arn
}


# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${local.app_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, { Name = "${local.app_name}-log-group" })
}

# ECS Cluster
resource "aws_ecs_cluster" "cloagent" {
  name = "${local.app_name}-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(var.tags, { Name = "${local.app_name}-cluster" })
}

# ECS Task Execution IAM Role (for pulling images, writing logs)
resource "aws_iam_role" "ecs_execution" {
  name = "${local.app_name}-ecs-execution-role"

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

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (app permissions: Bedrock, S3, Aurora, Secrets Manager)
resource "aws_iam_role" "ecs_task" {
  name = "${local.app_name}-ecs-task-role"

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

# Secrets Manager read access
# Secrets Manager read access (attached to execution role so ECS can inject at startup)
resource "aws_iam_role_policy" "secrets_read" {
  name = "${local.app_name}-secrets-read"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
        ]
        Resource = [
          aws_secretsmanager_secret.db_credentials.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
        ]
        Resource = [aws_kms_key.cloagent.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        Resource = ["arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:inference-profile/*"]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.ecs.arn}:*"
      }
    ]
  })
}

# ECS Task Definition
resource "aws_ecs_task_definition" "cloagent" {
  family                   = "${local.app_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name         = local.app_name
    image        = "${aws_ecr_repository.cloagent.repository_url}:latest"
    essential    = true
    portMappings = [{ containerPort = var.container_port, protocol = "tcp" }]

    environment = [
      { name = "ENVIRONMENT", value = var.environment },
      { name = "LOG_LEVEL", value = "INFO" },
      { name = "USE_MOCK_LLM", value = "false" },
      { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
      { name = "BEDROCK_REGION", value = var.aws_region },
      { name = "EMBEDDING_MODEL_ID", value = var.embedding_model_id },
      { name = "EMBEDDING_DIMENSIONS", value = tostring(var.embedding_dimensions) },
      { name = "DATABASE_URL", value = "" }, # set via secret
      { name = "S3_BUCKET", value = aws_s3_bucket.documents.id },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "SECRET_MANAGER_ARN", value = aws_secretsmanager_secret.db_credentials.arn },
      { name = "KMS_KEY_ID", value = aws_kms_key.cloagent.arn },
      { name = "AUDIT_ENABLED", value = "true" },
      { name = "RETRIEVAL_TOP_K", value = "10" },
      { name = "INGEST_SAMPLE_DOCS", value = "false" },
    ]

    # Secrets Manager — individual fields
    secrets = [
      {
        name      = "DB_USERNAME"
        valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:username::"
      },
      {
        name      = "DB_PASSWORD"
        valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:password::"
      },
      {
        name      = "DB_HOST"
        valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:host::"
      },
      {
        name      = "DB_PORT"
        valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:port::"
      },
      {
        name      = "DB_NAME"
        valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:dbname::"
      },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 30
    }
  }])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  tags = var.tags
}

# ECS Service
resource "aws_ecs_service" "cloagent" {
  name            = "${local.app_name}-service-${var.environment}"
  cluster         = aws_ecs_cluster.cloagent.id
  task_definition = aws_ecs_task_definition.cloagent.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  # Deployment
  deployment_controller {
    type = "ECS"
  }
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100
  health_check_grace_period_seconds  = 60

  # Network
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  # Load balancer
  load_balancer {
    target_group_arn = aws_lb_target_group.cloagent.arn
    container_name   = local.app_name
    container_port   = var.container_port
  }

  enable_execute_command = true # for debugging via ECS Exec

  depends_on = [aws_lb.cloagent]

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = var.tags
}

# ── Application Load Balancer ─────────────────────────────────────────────────

resource "aws_lb" "cloagent" {
  name               = "${local.app_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = var.enable_patrol_deletion_protection

  idle_timeout = 300

  tags = merge(var.tags, { Name = "${local.app_name}-alb" })
}

resource "aws_lb_target_group" "cloagent" {
  name        = "${local.app_name}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = try(aws_vpc.cloagent[0].id, var.existing_vpc_id)
  target_type = "ip"

  deregistration_delay = 30

  health_check {
    enabled             = true
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    matcher             = "200"
  }

  tags = var.tags
}

# HTTPS listener — only created when domain_name is set (cert available)
resource "aws_lb_listener" "https" {
  count = var.domain_name != "" ? 1 : 0

  load_balancer_arn = aws_lb.cloagent.arn
  port              = 443
  protocol          = "HTTPS"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.cloagent.arn
  }

  ssl_policy      = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn = var.domain_name != "" ? aws_acm_certificate.cloagent[0].arn : ""

  tags = var.tags
}

# HTTP → HTTPS redirect
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.cloagent.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  tags = var.tags
}
