#!/bin/bash
set -e

# Format logging helper
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "=== Starting Deployment ==="

# 1. Dependency Checks
log "Checking system dependencies..."
dependencies=(docker jq aws)
for cmd in "${dependencies[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log "Error: Required dependency '$cmd' is not installed."
        exit 1
    fi
done
log "All system dependencies verified."

# 2. Target Directory
DEPLOY_DIR="/opt/packvote"
log "Navigating to target directory: $DEPLOY_DIR..."
if [ ! -d "$DEPLOY_DIR" ]; then
    log "Error: Directory $DEPLOY_DIR does not exist. Please create it and set correct permissions."
    exit 1
fi
cd "$DEPLOY_DIR"

# 3. File Verification
log "Verifying docker-compose.yml exists..."
if [ ! -f docker-compose.yml ]; then
    log "Error: docker-compose.yml not found in $DEPLOY_DIR."
    exit 1
fi
log "docker-compose.yml verified."

# 4. AWS STS Identity & Region Retrieval
log "Retrieving AWS account details dynamically..."
AWS_REGION=$(aws configure get region 2>/dev/null || true)
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log "Targeting Region: $AWS_REGION | AWS Account: $AWS_ACCOUNT_ID"

# 5. ECR Login
log "Authenticating with Amazon ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID".dkr.ecr."$AWS_REGION".amazonaws.com
log "Successfully authenticated with Amazon ECR."

# 6. Retrieve Secrets & Generate .env
log "Fetching secret payload from AWS Secrets Manager..."
aws secretsmanager get-secret-value --secret-id packvote/production --region "$AWS_REGION" --query SecretString --output text | jq -r 'to_entries|map("\(.key)=\(.value)")|.[]' > .env

# Append registry configurations securely
echo "ECR_REGISTRY=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com" >> .env
echo "IMAGE_TAG=${IMAGE_TAG:-latest}" >> .env

# Verify .env is not empty and count variables
if [ ! -s .env ]; then
    log "Error: Generated .env file is empty."
    exit 1
fi
VAR_COUNT=$(wc -l < .env)
log "Generated .env file with $VAR_COUNT environment variables."

# 7. Pull and Restart Services
log "Pulling latest images from Amazon ECR..."
docker compose pull

log "Restarting containerized services..."
docker compose up -d --remove-orphans

log "Cleaning up old, unused Docker images..."
docker image prune -f

log "=== Deployment Completed Successfully ==="
