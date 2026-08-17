# ── Aurora PostgreSQL + pgvector ─���─────────────────────────────────────────────

# KMS Key for Aurora encryption
resource "aws_kms_key" "cloagent" {
  description             = "KMS key for CLO Agent encryption at rest"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = merge(var.tags, { Name = "${local.app_name}-kms" })
}

resource "aws_kms_alias" "cloagent" {
  name          = "alias/${local.app_name}"
  target_key_id = aws_kms_key.cloagent.key_id
}

# Aurora Cluster (Serverless v2)
resource "aws_rds_cluster" "cloagent" {
  cluster_identifier = "${local.app_name}-aurora-${var.environment}"
  engine             = "aurora-postgresql"
  engine_version     = "15.10"
  engine_mode        = "provisioned" # Serverless v2 uses "provisioned"
  serverlessv2_scaling_configuration {
    min_capacity = var.aurora_serverless_v2_min_capacity
    max_capacity = var.aurora_serverless_v2_max_capacity
  }

  database_name   = var.db_name
  master_username = var.db_username
  master_password = random_password.db_password.result

  # Networking
  vpc_security_group_ids = [aws_security_group.aurora.id]
  db_subnet_group_name   = aws_db_subnet_group.cloagent.name

  # Encryption
  kms_key_id                   = aws_kms_key.cloagent.arn
  storage_encrypted            = true
  backup_retention_period      = 7
  preferred_backup_window      = "03:00-04:00"
  preferred_maintenance_window = "mon:04:00-mon:05:00"

  # Publicly accessible = false (private VPC only)

  skip_final_snapshot       = !var.enable_patrol_deletion_protection
  final_snapshot_identifier = var.enable_patrol_deletion_protection ? "${local.app_name}-final-snapshot" : null

  tags = merge(var.tags, { Name = "${local.app_name}-aurora" })
}

# Cluster Instance (Writer)
resource "aws_rds_cluster_instance" "writer" {
  identifier         = "${local.app_name}-aurora-writer"
  cluster_identifier = aws_rds_cluster.cloagent.id
  instance_class     = "db.serverless" # Serverless v2
  engine             = aws_rds_cluster.cloagent.engine
  engine_version     = aws_rds_cluster.cloagent.engine_version

  # Auto-generate CA cert

  tags = merge(var.tags, { Name = "${local.app_name}-aurora-writer" })
}

# Cluster Instance (Reader — optional for read scaling)
resource "aws_rds_cluster_instance" "reader" {
  count              = var.environment == "production" ? 1 : 0
  identifier         = "${local.app_name}-aurora-reader"
  cluster_identifier = aws_rds_cluster.cloagent.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.cloagent.engine
  engine_version     = aws_rds_cluster.cloagent.engine_version

  tags = merge(var.tags, { Name = "${local.app_name}-aurora-reader" })
}

# DB Subnet Group
resource "aws_db_subnet_group" "cloagent" {
  name       = "${local.app_name}-aurora-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(var.tags, { Name = "${local.app_name}-aurora-subnet-group" })
}

# Random password for DB (stored in Secrets Manager)
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Secrets Manager — DB Credentials
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${local.app_name}/db-credentials"
  description             = "CLO Agent Aurora database credentials"
  recovery_window_in_days = 7
  kms_key_id              = aws_kms_key.cloagent.arn

  tags = merge(var.tags, { Name = "${local.app_name}-db-credentials" })
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
    host     = aws_rds_cluster.cloagent.endpoint
    port     = aws_rds_cluster.cloagent.port
    dbname   = var.db_name
    engine   = "postgresql"
  })
}
