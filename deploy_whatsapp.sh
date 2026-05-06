#!/bin/bash
set -e

ACCOUNT_ID="640168409035"
REGION="us-east-1"
PROFILE="agendawa"
REPO_NAME="users-api-whatsapp-webhook-dev"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:latest"

cd "$(dirname "$0")"
ROOT_DIR="$(pwd)"

echo "==> 1. Creando repositorio ECR..."
cd terraform/environments/dev
terraform init -reconfigure 2>/dev/null || terraform init
terraform apply -target=module.lambda.aws_ecr_repository.whatsapp_webhook -auto-approve

echo "==> 2. Autenticando en ECR..."
aws ecr get-login-password --region "$REGION" --profile "$PROFILE" | \
  docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "==> 3. Construyendo imagen Docker (esto tarda varios minutos)..."
cd "$ROOT_DIR"
docker build -f Dockerfile.whatsapp -t "$IMAGE_URI" .

echo "==> 4. Subiendo imagen a ECR..."
docker push "$IMAGE_URI"

echo "==> 5. Desplegando Lambda..."
cd terraform/environments/dev
terraform apply -auto-approve

echo ""
echo "✓ Listo. Lambda whatsapp-webhook-dev actualizada con faster-whisper."
echo "  Imagen: ${IMAGE_URI}"
