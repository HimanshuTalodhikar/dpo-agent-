# ── Networking: VPC, Subnets, NAT, IGW, Security Groups ─────────────────────���─

# VPC
resource "aws_vpc" "cloagent" {
  count                = var.existing_vpc_id != "" ? 0 : 1
  cidr_block           = local.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, { Name = "${local.app_name}-vpc" })
}

# Internet Gateway
resource "aws_internet_gateway" "cloagent" {
  count  = var.existing_vpc_id != "" ? 0 : 1
  vpc_id = aws_vpc.cloagent[0].id

  tags = merge(var.tags, { Name = "${local.app_name}-igw" })
}

# Public Subnets (for ALB + NAT Gateway)
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = try(aws_vpc.cloagent[0].id, var.existing_vpc_id)
  cidr_block              = cidrsubnet(local.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false

  tags = merge(var.tags, { Name = "${local.app_name}-public-subnet-${count.index + 1}" })
}

# Private Subnets (for ECS tasks + Aurora)
resource "aws_subnet" "private" {
  count                   = 2
  vpc_id                  = try(aws_vpc.cloagent[0].id, var.existing_vpc_id)
  cidr_block              = cidrsubnet(local.vpc_cidr, 8, count.index + 2)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false

  tags = merge(var.tags, { Name = "${local.app_name}-private-subnet-${count.index + 1}" })
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  count  = var.existing_vpc_id != "" ? 0 : 1
  domain = "vpc"

  tags = merge(var.tags, { Name = "${local.app_name}-nat-eip" })
}

# NAT Gateway (in public subnet, so ECS tasks in private can reach internet)
resource "aws_nat_gateway" "cloagent" {
  count         = var.existing_vpc_id != "" ? 0 : 1
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = merge(var.tags, { Name = "${local.app_name}-nat" })
}

# Private Route Table (ECS + Aurora)
resource "aws_route_table" "private" {
  count  = var.existing_vpc_id != "" ? 0 : 1
  vpc_id = try(aws_vpc.cloagent[0].id, var.existing_vpc_id)

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.cloagent[0].id
  }

  tags = merge(var.tags, { Name = "${local.app_name}-private-rt" })
}

# Public Route Table (ALB)
resource "aws_route_table" "public" {
  count  = var.existing_vpc_id != "" ? 0 : 1
  vpc_id = try(aws_vpc.cloagent[0].id, var.existing_vpc_id)

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.cloagent[0].id
  }

  tags = merge(var.tags, { Name = "${local.app_name}-public-rt" })
}

# Route table associations
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[0].id
}

# Security Group: ECS Tasks (allow ALB + Aurora + S3)
resource "aws_security_group" "ecs_tasks" {
  name        = "${local.app_name}-ecs-tasks"
  description = "Security group for ECS Fargate tasks"
  vpc_id      = try(aws_vpc.cloagent[0].id, var.existing_vpc_id)

  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [aws_security_group.alb.id]
    description     = "Allow traffic from ALB"
  }

  # All outbound HTTPS — covers Bedrock, S3, and all other AWS APIs
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = merge(var.tags, { Name = "${local.app_name}-ecs-tasks-sg" })
}

# Security Group: Aurora (only from ECS SG)
resource "aws_security_group" "aurora" {
  name        = "${local.app_name}-aurora"
  description = "Security group for Aurora PostgreSQL"
  vpc_id      = try(aws_vpc.cloagent[0].id, var.existing_vpc_id)

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
    description     = "Allow PostgreSQL from ECS tasks"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${local.app_name}-aurora-sg" })
}

# Security Group: ALB (public)
resource "aws_security_group" "alb" {
  name        = "${local.app_name}-alb"
  description = "Security group for Application Load Balancer"
  vpc_id      = try(aws_vpc.cloagent[0].id, var.existing_vpc_id)

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = length(var.allowed_cidr_blocks) > 0 ? var.allowed_cidr_blocks : ["0.0.0.0/0"]
    description = "HTTPS from anywhere"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = length(var.allowed_cidr_blocks) > 0 ? var.allowed_cidr_blocks : ["0.0.0.0/0"]
    description = "HTTP redirect"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${local.app_name}-alb-sg" })
}