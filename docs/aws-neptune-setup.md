# AWS Neptune + OpenSearch Serverless Setup Guide

## Existing Resources (Account: 430896782648, Region: ap-south-1)

| Resource | Name/ID | Status |
|---|---|---|
| Neptune Cluster | `cloagent-govt` | ✅ AVAILABLE |
| Neptune Engine | 1.4.8.0 Serverless (0.5–2.0 NCU) | ✅ |
| Neptune Writer Endpoint | `cloagent-govt.cluster-cbk4moqeonjo.ap-south-1.neptune.amazonaws.com:8182` | ✅ |
| AOSS Collection | `cloagent-govt` (ID: `8bj12teqwj4xh6vuv5k7`) | ✅ ACTIVE |
| AOSS Endpoint | `https://8bj12teqwj4xh6vuv5k7.ap-south-1.aoss.amazonaws.com` | ✅ |
| AOSS Data Access Policy | `cloagent-data-access` | ✅ |
| S3 Bucket | `cloagent-documents` | ✅ CREATED |
| Neptune Security Group | `sg-09d9c6476e1558cf6` (cloagent-neptune) | ✅ |
| Neptune VPC | `vpc-0022f6f3f77ea71a7` (172.31.0.0/16) | ✅ |
| Neptune Subnet Group | `cloagent-neptune-subnet` | ✅ |

## Security Group Rules

Neptune SG `sg-09d9c6476e1558cf6`:
- Port 8182 from `sg-0bc0643e53df7c9f1` (app SG)
- Port 8182 from developer IP (temp, for local dev)
- Port 443 from `0.0.0.0/0` (outbound HTTPS for AOSS)

## Local Development Access

Neptune is NOT publicly accessible by default. To test locally:

```bash
# Add your current IP to Neptune SG (temporary)
MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress \
  --group-id sg-09d9c6476e1558cf6 \
  --protocol tcp \
  --port 8182 \
  --cidr ${MY_IP}/32 \
  --region ap-south-1

# Remove when done
aws ec2 revoke-security-group-ingress \
  --group-id sg-09d9c6476e1558cf6 \
  --protocol tcp \
  --port 8182 \
  --cidr ${MY_IP}/32 \
  --region ap-south-1
```

> **Security Note**: NEVER add `0.0.0.0/0` to Neptune port 8182. Always use specific IPs.

## Production (ECS Fargate)

For ECS deployment, add the ECS task security group to Neptune SG:

```bash
# Allow ECS tasks to reach Neptune
aws ec2 authorize-security-group-ingress \
  --group-id sg-09d9c6476e1558cf6 \
  --protocol tcp \
  --port 8182 \
  --source-group <ecs-task-sg-id> \
  --region ap-south-1
```

## IAM Permissions Required

The application needs these permissions to call Neptune + AOSS:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "NeptuneConnect",
      "Effect": "Allow",
      "Action": ["neptune-db:connect"],
      "Resource": "arn:aws:rds:ap-south-1:430896782648:cluster:cloagent-govt"
    },
    {
      "Sid": "AOSSAccess",
      "Effect": "Allow",
      "Action": ["aoss:APIAccessAll"],
      "Resource": "arn:aws:aoss:ap-south-1:430896782648:collection/8bj12teqwj4xh6vuv5k7"
    },
    {
      "Sid": "S3Documents",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::cloagent-documents",
        "arn:aws:s3:::cloagent-documents/*"
      ]
    }
  ]
}
```

## Neptune Connectivity Test

```bash
# Test connectivity to Neptune endpoint (from within the VPC or with IP allowed)
curl -s -o /dev/null -w "%{http_code}" \
  https://cloagent-govt.cluster-cbk4moqeonjo.ap-south-1.neptune.amazonaws.com:8182/status
# Expected: 200
```

## AOSS Test

```bash
# Test AOSS endpoint (uses AWS SigV4)
aws opensearchserverless batch-get-collection \
  --ids 8bj12teqwj4xh6vuv5k7 \
  --region ap-south-1 \
  --query 'collectionDetails[0].status'
# Expected: "ACTIVE"
```

## Neptune Engine Notes

- Engine: 1.4.8.0 supports openCypher (used by Graphiti via `langchain_aws.NeptuneGraph`)
- IAM authentication is **disabled** on this cluster
- Authentication handled by AWS SigV4 signing at the HTTP request level (langchain_aws handles this)
- Encryption at rest: KMS (`arn:aws:kms:ap-south-1:430896782648:key/b0a4e9f6-ee11-4fa8-b677-a13c9ad1316d`)
