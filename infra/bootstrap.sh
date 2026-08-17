#!/usr/bin/env bash
# ── Terraform State Bootstrap ───���─────────────────────────────────────────────
# Run ONCE before `terraform init` to create the S3 bucket + DynamoDB table
# that store Terraform state and lock records.
#
# Usage:
#   chmod +x bootstrap.sh
#   ./bootstrap.sh [region]
#
# Default region: us-east-1

set -e

REGION="${1:-us-east-1}"
STATE_BUCKET="cloagent-terraform-state-430896782648"
DDB_TABLE="cloagent-terraform-locks"
PROFILE="${AWS_PROFILE:-default}"

echo "=== Terraform State Bootstrap ==="
echo "Region: $REGION"
echo "Bucket: $STATE_BUCKET"
echo ""

# ── S3 bucket for state ───────────────────────────────────────────────────────
echo "[1/3] Creating S3 bucket for Terraform state..."
if aws s3api head-bucket --bucket "$STATE_BUCKET" --profile "$PROFILE" 2>/dev/null; then
    echo "  S3 bucket already exists: $STATE_BUCKET"
else
    aws s3api create-bucket \
        --bucket "$STATE_BUCKET" \
        --region "$REGION" \
        $([ "$REGION" != "us-east-1" ] && echo "--create-bucket-configuration LocationConstraint=$REGION") \
        --profile "$PROFILE" \
        > /dev/null
    echo "  Created S3 bucket: $STATE_BUCKET"

    # Enable versioning (required for Terraform state)
    aws s3api put-bucket-versioning \
        --bucket "$STATE_BUCKET" \
        --versioning-configuration Status=Enabled \
        --profile "$PROFILE"

    # Block public access
    aws s3api put-public-access-block \
        --bucket "$STATE_BUCKET" \
        --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
        --profile "$PROFILE"

    # Encryption
    aws s3api put-bucket-encryption \
        --bucket "$STATE_BUCKET" \
        --server-side-encryption-configuration \
            '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' \
        --profile "$PROFILE"

    # Prevent accidental deletion — write to temp file to avoid shell escaping issues
    LC_FILE=$(mktemp)
    cat > "$LC_FILE" << 'LCEOF'
{
  "Rules": [{
    "ID": "prevent-delete",
    "Status": "Enabled",
    "NoncurrentVersionExpiration": {"NoncurrentDays": 365}
  }]
}
LCEOF
    aws s3api put-bucket-lifecycle-configuration \
        --bucket "$STATE_BUCKET" \
        --lifecycle-configuration "file://$LC_FILE" \
        --profile "$PROFILE"
    rm -f "$LC_FILE"

    echo "  Bucket configured: versioning on, encrypted, lifecycle set"
fi

# ── DynamoDB table for state locks ────────────────────────────────────────────
echo "[2/3] Creating DynamoDB table for Terraform state locks..."
if aws dynamodb describe-table --table-name "$DDB_TABLE" --profile "$PROFILE" 2>/dev/null; then
    echo "  DynamoDB table already exists: $DDB_TABLE"
else
    aws dynamodb create-table \
        --table-name "$DDB_TABLE" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$REGION" \
        --profile "$PROFILE" \
        > /dev/null
    echo "  Created DynamoDB table: $DDB_TABLE"
fi

# ── Done ─────────────────────���────────────────────────────────────────────────
echo ""
echo "[3/3] Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  cd infra"
echo "  terraform init"
echo ""
echo "Terraform backend config (in main.tf) uses:"
echo "  bucket         = \"$STATE_BUCKET\""
echo "  dynamodb_table = \"$DDB_TABLE\""
