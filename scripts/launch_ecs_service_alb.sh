#!/usr/bin/env bash
# ==============================================================================
# Launch Active AWS ECS Fargate Service with Application Load Balancer (ALB)
# ==============================================================================
# Provisions VPC Security Groups, ALB, Target Groups, HTTP Listener,
# and creates the active ECS Fargate Service running 2 replica tasks.
# ==============================================================================

set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
CLUSTER_NAME="cloagent-prod-cluster"
SERVICE_NAME="cloagent-mcp-service"
TASK_DEF_FAMILY="cloagent-mcp-task"
ALB_NAME="cloagent-alb"
TG_NAME="cloagent-tg"
SG_NAME="cloagent-ecs-sg"

echo "======================================================================"
echo " Launching AWS ECS Fargate Service behind ALB in ${AWS_REGION}"
echo "======================================================================"

# 1. Fetch Default VPC & Subnets
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --region "${AWS_REGION}" --query "Vpcs[0].VpcId" --output text)

if [ -z "${VPC_ID}" ] || [ "${VPC_ID}" = "None" ]; then
    echo "Default VPC not found. Fetching first available VPC..."
    VPC_ID=$(aws ec2 describe-vpcs --region "${AWS_REGION}" --query "Vpcs[0].VpcId" --output text)
fi

echo "  -> Using VPC ID: ${VPC_ID}"

SUBNET_IDS=($(aws ec2 describe-subnets --filters Name=vpc-id,Values="${VPC_ID}" --region "${AWS_REGION}" --query "Subnets[*].SubnetId" --output text))
if [ ${#SUBNET_IDS[@]} -lt 2 ]; then
    echo "ERROR: At least 2 subnets are required for ALB. Found ${#SUBNET_IDS[@]}."
    exit 1
fi

SUBNET_1="${SUBNET_IDS[0]}"
SUBNET_2="${SUBNET_IDS[1]}"
SUBNET_CSV=$(IFS=,; echo "${SUBNET_IDS[*]}")
echo "  -> Using Subnets: ${SUBNET_1}, ${SUBNET_2}"

# 2. Create Security Group
echo "[1/4] Provisioning Security Group: ${SG_NAME}..."
SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values="${SG_NAME}" Name=vpc-id,Values="${VPC_ID}" --region "${AWS_REGION}" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || true)

if [ -z "${SG_ID}" ] || [ "${SG_ID}" = "None" ]; then
    SG_ID=$(aws ec2 create-security-group \
        --group-name "${SG_NAME}" \
        --description "Security group for CLO Agent MCP Server on ECS Fargate" \
        --vpc-id "${VPC_ID}" \
        --region "${AWS_REGION}" \
        --query "GroupId" \
        --output text)

    # Allow Inbound Traffic on Port 80 (HTTP) & 8000 (MCP Application)
    aws ec2 authorize-security-group-ingress \
        --group-id "${SG_ID}" \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region "${AWS_REGION}"

    aws ec2 authorize-security-group-ingress \
        --group-id "${SG_ID}" \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region "${AWS_REGION}" &>/dev/null || true

    aws ec2 authorize-security-group-ingress \
        --group-id "${SG_ID}" \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0 \
        --region "${AWS_REGION}" &>/dev/null || true

    echo "  -> Created Security Group: ${SG_ID}"
else
    echo "  -> Security Group exists: ${SG_ID}"
fi

# 3. Create Application Load Balancer & Target Group
echo "[2/4] Provisioning Application Load Balancer (${ALB_NAME}) & Target Group (${TG_NAME})..."

# Target Group (IP type required for ECS Fargate)
TG_ARN=$(aws elbv2 describe-target-groups --names "${TG_NAME}" --region "${AWS_REGION}" --query "TargetGroups[0].TargetGroupArn" --output text 2>/dev/null || true)

if [ -z "${TG_ARN}" ] || [ "${TG_ARN}" = "None" ]; then
    TG_ARN=$(aws elbv2 create-target-group \
        --name "${TG_NAME}" \
        --protocol HTTP \
        --port 8000 \
        --vpc-id "${VPC_ID}" \
        --target-type ip \
        --health-check-protocol HTTP \
        --health-check-path "/health" \
        --health-check-interval-seconds 30 \
        --region "${AWS_REGION}" \
        --query "TargetGroups[0].TargetGroupArn" \
        --output text)
    echo "  -> Created Target Group: ${TG_ARN}"
else
    echo "  -> Target Group exists: ${TG_ARN}"
fi

# ALB
ALB_ARN=$(aws elbv2 describe-load-balancers --names "${ALB_NAME}" --region "${AWS_REGION}" --query "LoadBalancers[0].LoadBalancerArn" --output text 2>/dev/null || true)

if [ -z "${ALB_ARN}" ] || [ "${ALB_ARN}" = "None" ]; then
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name "${ALB_NAME}" \
        --subnets "${SUBNET_1}" "${SUBNET_2}" \
        --security-groups "${SG_ID}" \
        --scheme internet-facing \
        --type application \
        --region "${AWS_REGION}" \
        --query "LoadBalancers[0].LoadBalancerArn" \
        --output text)
    echo "  -> Created Application Load Balancer: ${ALB_ARN}"
else
    echo "  -> Application Load Balancer exists: ${ALB_ARN}"
fi

# Ensure ALB idle_timeout is 300 seconds (prevents HTTP 504 Gateway Timeout during LLM calls)
aws elbv2 modify-load-balancer-attributes \
    --load-balancer-arn "${ALB_ARN}" \
    --attributes Key=idle_timeout.timeout_seconds,Value=300 \
    --region "${AWS_REGION}" &>/dev/null || true

# Get ALB DNS Name
ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns "${ALB_ARN}" --region "${AWS_REGION}" --query "LoadBalancers[0].DNSName" --output text)

# HTTP Listener on Port 80
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn "${ALB_ARN}" --region "${AWS_REGION}" --query "Listeners[0].ListenerArn" --output text 2>/dev/null || true)

if [ -z "${LISTENER_ARN}" ] || [ "${LISTENER_ARN}" = "None" ]; then
    aws elbv2 create-listener \
        --load-balancer-arn "${ALB_ARN}" \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn="${TG_ARN}" \
        --region "${AWS_REGION}" &>/dev/null || true
    echo "  -> Created HTTP Listener on Port 80"
fi

# 4. Create or Update AWS ECS Fargate Service
echo "[3/4] Deploying AWS ECS Fargate Service (${SERVICE_NAME})..."

if aws ecs describe-services --cluster "${CLUSTER_NAME}" --services "${SERVICE_NAME}" --region "${AWS_REGION}" --query "services[0].status" --output text 2>/dev/null | grep -q "ACTIVE"; then
    echo "  -> Updating existing active ECS service..."
    aws ecs update-service \
        --cluster "${CLUSTER_NAME}" \
        --service "${SERVICE_NAME}" \
        --force-new-deployment \
        --region "${AWS_REGION}" &>/dev/null
else
    echo "  -> Launching new ECS Fargate service..."
    aws ecs create-service \
        --cluster "${CLUSTER_NAME}" \
        --service-name "${SERVICE_NAME}" \
        --task-definition "${TASK_DEF_FAMILY}:1" \
        --desired-count 2 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_1},${SUBNET_2}],securityGroups=[${SG_ID}],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=${TG_ARN},containerName=cloagent-mcp-app,containerPort=8000" \
        --region "${AWS_REGION}" &>/dev/null
    echo "  -> Created ECS Fargate Service: ${SERVICE_NAME}"
fi

# 5. Final Summary
echo ""
echo "======================================================================"
echo " AWS ECS FARGATE SERVICE LAUNCHED SUCCESSFULLY!"
echo "======================================================================"
echo " Service Name:    ${SERVICE_NAME}"
echo " ECS Cluster:     ${CLUSTER_NAME}"
echo " Desired Tasks:   2 Replicas (High-Availability)"
echo " ALB Endpoint:    http://${ALB_DNS}"
echo " Health Check:    http://${ALB_DNS}/health"
echo " MCP Tools API:   http://${ALB_DNS}/mcp/tools"
echo "======================================================================"
