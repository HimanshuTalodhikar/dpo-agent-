#!/usr/bin/env bash
# ==============================================================================
# Build, Push to ECR, and Deploy to AWS ECS Fargate
# ==============================================================================
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
ACCOUNT_ID="430896782648"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/cloagent-mcp-server"
CLUSTER_NAME="cloagent-prod-cluster"
SERVICE_NAME="cloagent-mcp-service"
TASK_DEF_FAMILY="cloagent-mcp-task"

echo "======================================================================"
echo " 1. Authenticating with AWS ECR..."
echo "======================================================================"
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "======================================================================"
echo " 2. Building Docker Image for linux/amd64..."
echo "======================================================================"
docker build --platform linux/amd64 -t "${ECR_URI}:latest" .

echo "======================================================================"
echo " 3. Pushing Docker Image to AWS ECR..."
echo "======================================================================"
docker push "${ECR_URI}:latest"

echo "======================================================================"
echo " 4. Deploying / Updating AWS ECS Fargate Task..."
echo "======================================================================"
# Check if ECS service exists, if not run standalone task or create service
if aws ecs describe-services --cluster "${CLUSTER_NAME}" --services "${SERVICE_NAME}" --region "${AWS_REGION}" | grep -q "ACTIVE"; then
    echo "Updating existing ECS service ${SERVICE_NAME}..."
    aws ecs update-service --cluster "${CLUSTER_NAME}" --service "${SERVICE_NAME}" --force-new-deployment --region "${AWS_REGION}"
else
    echo "ECS service does not exist yet. Task Definition ${TASK_DEF_FAMILY} is ready for ECS service deployment."
fi

echo "======================================================================"
echo " AWS ECR BUILD, PUSH & DEPLOYMENT COMPLETE SUCCESS!"
echo " ECR Image: ${ECR_URI}:latest"
echo "======================================================================"
