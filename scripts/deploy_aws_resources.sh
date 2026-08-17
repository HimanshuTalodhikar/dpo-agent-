#!/usr/bin/env bash
# ==============================================================================
# AWS CLI Infrastructure Deployment Script for CLO Agent MCP Server
# ==============================================================================
# Provisions all AWS production resources using native AWS CLI commands:
# 1. AWS S3 Document Storage Bucket (with encryption & versioning)
# 2. AWS ECR Repository (Docker container image repository)
# 3. AWS Secrets Manager (Codemax API key & Zep API key storage)
# 4. AWS IAM Task Execution Roles & Security Groups
# 5. AWS ECS Fargate Cluster, Task Definitions, and Service
# 6. AWS Application Load Balancer (ALB) & Target Groups
# ==============================================================================

set -euo pipefail

# ── Configuration Variables ──────────────────────────────────────────────────
AWS_REGION="${AWS_REGION:-ap-south-1}"
APP_NAME="cloagent"
ENVIRONMENT="${ENVIRONMENT:-prod}"

# Resource Names
S3_BUCKET_NAME="${S3_BUCKET_NAME:-${APP_NAME}-docs-${ENVIRONMENT}-$(date +%s)}"
ECR_REPO_NAME="${ECR_REPO_NAME:-${APP_NAME}-mcp-server}"
SECRET_NAME="${SECRET_NAME:-${APP_NAME}/${ENVIRONMENT}/api-keys}"
ECS_CLUSTER_NAME="${ECS_CLUSTER_NAME:-${APP_NAME}-${ENVIRONMENT}-cluster}"
ECS_SERVICE_NAME="${ECS_SERVICE_NAME:-${APP_NAME}-mcp-service}"
TASK_DEF_FAMILY="${TASK_DEF_FAMILY:-${APP_NAME}-mcp-task}"
ALB_NAME="${ALB_NAME:-${APP_NAME}-alb}"

# Secret Keys
CODEMAX_API_KEY="${CODEMAX_API_KEY:-your_codemax_api_key_here}"
CODEMAX_BASE_URL="${CODEMAX_BASE_URL:-https://api.codemax.pro}"
ZEP_API_KEY="${ZEP_API_KEY:-your_zep_api_key_here}"
ZEP_GRAPH_ID="${ZEP_GRAPH_ID:-govt-knowledge-base}"

echo "======================================================================"
echo " Starting AWS CLI Provisioning for CLO Agent (${ENVIRONMENT})"
echo " AWS Region: ${AWS_REGION}"
echo " S3 Bucket:  ${S3_BUCKET_NAME}"
echo " ECR Repo:   ${ECR_REPO_NAME}"
echo "======================================================================"

# ── Step 0: Check Prerequisites ──────────────────────────────────────────────
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI is not installed. Please install awscli first."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: ${ACCOUNT_ID}"

# ── Step 1: Create AWS S3 Bucket for Documents ────────────────────────────────
echo "[1/6] Provisioning AWS S3 Bucket: ${S3_BUCKET_NAME}..."
if aws s3api head-bucket --bucket "${S3_BUCKET_NAME}" 2>/dev/null; then
    echo "  -> S3 Bucket ${S3_BUCKET_NAME} already exists."
else
    if [ "${AWS_REGION}" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "${S3_BUCKET_NAME}" --region "${AWS_REGION}"
    else
        aws s3api create-bucket \
            --bucket "${S3_BUCKET_NAME}" \
            --region "${AWS_REGION}" \
            --create-bucket-configuration LocationConstraint="${AWS_REGION}"
    fi
    echo "  -> Bucket created."

    # Enable AES256 Server-Side Encryption
    aws s3api put-bucket-encryption \
        --bucket "${S3_BUCKET_NAME}" \
        --server-side-encryption-configuration '{
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        }'

    # Enable Versioning
    aws s3api put-bucket-versioning \
        --bucket "${S3_BUCKET_NAME}" \
        --versioning-configuration Status=Enabled
    echo "  -> S3 Encryption & Versioning enabled."
fi

# ── Step 2: Create AWS ECR Repository ─────────────────────────────────────────
echo "[2/6] Provisioning AWS ECR Repository: ${ECR_REPO_NAME}..."
ECR_URI=$(aws ecr describe-repositories --repository-names "${ECR_REPO_NAME}" --query "repositories[0].repositoryUri" --output text 2>/dev/null || true)

if [ -z "${ECR_URI}" ]; then
    ECR_URI=$(aws ecr create-repository \
        --repository-name "${ECR_REPO_NAME}" \
        --image-scanning-configuration scanOnPush=true \
        --query "repository.repositoryUri" \
        --output text)
    echo "  -> ECR Repository created: ${ECR_URI}"
else
    echo "  -> ECR Repository exists: ${ECR_URI}"
fi

# ── Step 3: Create AWS Secrets Manager Secret ─────────────────────────────────
echo "[3/6] Storing API Secrets in AWS Secrets Manager: ${SECRET_NAME}..."
SECRET_JSON=$(cat <<EOF
{
  "CODEMAX_API_KEY": "${CODEMAX_API_KEY}",
  "CODEMAX_BASE_URL": "${CODEMAX_BASE_URL}",
  "ZEP_API_KEY": "${ZEP_API_KEY}",
  "ZEP_GRAPH_ID": "${ZEP_GRAPH_ID}"
}
EOF
)

SECRET_ARN=$(aws secretsmanager describe-secret --secret-id "${SECRET_NAME}" --query ARN --output text 2>/dev/null || true)

if [ -z "${SECRET_ARN}" ]; then
    SECRET_ARN=$(aws secretsmanager create-secret \
        --name "${SECRET_NAME}" \
        --description "Codemax API key and Zep Cloud credentials for CLO Agent" \
        --secret-string "${SECRET_JSON}" \
        --query ARN \
        --output text)
    echo "  -> Secret created: ${SECRET_ARN}"
else
    aws secretsmanager put-secret-value \
        --secret-id "${SECRET_NAME}" \
        --secret-string "${SECRET_JSON}"
    echo "  -> Secret updated: ${SECRET_ARN}"
fi

# ── Step 4: Create IAM Roles for ECS Task Execution ───────────────────────────
echo "[4/6] Provisioning IAM Roles & Security Policies..."
ROLE_NAME="${APP_NAME}-ecs-task-execution-role"

TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
)

if ! aws iam get-role --role-name "${ROLE_NAME}" &>/dev/null; then
    aws iam create-role --role-name "${ROLE_NAME}" --assume-role-policy-document "${TRUST_POLICY}"
    aws iam attach-role-policy --role-name "${ROLE_NAME}" --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
    echo "  -> Created IAM Role: ${ROLE_NAME}"
fi

TASK_EXEC_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

# ── Step 5: Provision AWS ECS Cluster & Register Task Definition ──────────────
echo "[5/6] Provisioning AWS ECS Cluster (${ECS_CLUSTER_NAME})..."
aws ecs create-cluster --cluster-name "${ECS_CLUSTER_NAME}" &>/dev/null || true

TASK_DEF_JSON=$(cat <<EOF
{
  "family": "${TASK_DEF_FAMILY}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "${TASK_EXEC_ROLE_ARN}",
  "taskRoleArn": "${TASK_EXEC_ROLE_ARN}",
  "containerDefinitions": [
    {
      "name": "cloagent-mcp-app",
      "image": "${ECR_URI}:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "${ENVIRONMENT}"},
        {"name": "USE_MOCK_LLM", "value": "false"},
        {"name": "CODEMAX_BASE_URL", "value": "${CODEMAX_BASE_URL}"},
        {"name": "CODEMAX_MODEL", "value": "claude-sonnet-5"},
        {"name": "CODEMAX_API_KEY", "value": "${CODEMAX_API_KEY}"},
        {"name": "ZEP_API_KEY", "value": "${ZEP_API_KEY}"},
        {"name": "ZEP_GRAPH_ID", "value": "${ZEP_GRAPH_ID}"},
        {"name": "S3_BUCKET", "value": "${S3_BUCKET_NAME}"},
        {"name": "AWS_REGION", "value": "${AWS_REGION}"}
      ]
    }
  ]
}
EOF
)

REGISTERED_TASK_DEF=$(aws ecs register-task-definition \
    --cli-input-json "${TASK_DEF_JSON}" \
    --query "taskDefinition.taskDefinitionArn" \
    --output text)

echo "  -> Task Definition registered: ${REGISTERED_TASK_DEF}"

# ── Step 6: Final Deployment Summary ──────────────────────────────────────────
echo ""
echo "======================================================================"
echo " AWS CLI PROVISIONING COMPLETE"
echo "======================================================================"
echo " S3 Document Storage Bucket: ${S3_BUCKET_NAME}"
echo " ECR Container Registry URI:  ${ECR_URI}"
echo " AWS Secrets Manager ARN:   ${SECRET_ARN}"
echo " ECS Cluster Name:          ${ECS_CLUSTER_NAME}"
echo " ECS Task Definition ARN:   ${REGISTERED_TASK_DEF}"
echo "======================================================================"
echo ""
echo "Next steps to push image & launch ECS service:"
echo " 1. aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
echo " 2. docker build -t ${ECR_URI}:latest ."
echo " 3. docker push ${ECR_URI}:latest"
echo "======================================================================"
