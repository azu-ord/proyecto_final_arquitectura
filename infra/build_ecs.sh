#!/bin/bash
# Build and push Docker image for ECS Fargate app
# Ejecutar desde la raíz del proyecto: bash infra/build_ecs.sh
#
# Variables requeridas (editar antes de ejecutar):
#   DB_HOST_PRIMARY    — endpoint de RDS primary
#   DB_HOST_REPLICA    — endpoint de RDS replica
#   RDS_SG_ID          — Security Group ID de RDS
#   SECRET_ARN         — ARN completo del secreto en Secrets Manager

set -euo pipefail  # FIX: detener en cualquier error, no continuar con imagen rota

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN — cargada desde .env (nunca subir a GitHub)
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "${SCRIPT_DIR}/../.env" ] && source "${SCRIPT_DIR}/../.env"

DB_HOST_PRIMARY="${DB_HOST_PRIMARY:?'Falta DB_HOST_PRIMARY — agrégalo a .env'}"
DB_HOST_REPLICA="${DB_HOST_REPLICA:?'Falta DB_HOST_REPLICA — agrégalo a .env'}"
RDS_SG_ID="${RDS_SG_ID:?'Falta RDS_SG_ID — agrégalo a .env'}"
SECRET_ARN="${SECRET_ARN:?'Falta SECRET_ARN — agrégalo a .env'}"

STACK_NAME="auto-repair-shop-app"
SERVICE_NAME="auto-repair-shop"
REGION="us-east-1"

# ─────────────────────────────────────────────────────────────────────────────
# Moverse a la raíz del proyecto (un nivel arriba de infra/)
# ─────────────────────────────────────────────────────────────────────────────
cd "$(dirname "$0")/.." || exit 1

# ─────────────────────────────────────────────────────────────────────────────
# Paso 1: Crear el repositorio ECR (idempotente — no falla si ya existe)
# ─────────────────────────────────────────────────────────────────────────────
echo ">>> [1/5] Creando repositorio ECR (si no existe)..."
# FIX: 2>/dev/null || true para que no falle si el repo ya existe
aws ecr create-repository \
    --repository-name "${SERVICE_NAME}" \
    --region "${REGION}" 2>/dev/null || true

ECR_URI=$(aws ecr describe-repositories \
    --repository-names "${SERVICE_NAME}" \
    --region "${REGION}" \
    --query "repositories[0].repositoryUri" \
    --output text)

echo "    ECR URI: ${ECR_URI}"

# ─────────────────────────────────────────────────────────────────────────────
# Paso 2: Autenticarse en ECR y hacer build + push
# ─────────────────────────────────────────────────────────────────────────────
echo ">>> [2/5] Autenticando en ECR..."
aws ecr get-login-password --region "${REGION}" | \
    docker login --username AWS --password-stdin \
    "$(aws sts get-caller-identity --query Account --output text).dkr.ecr.${REGION}.amazonaws.com"

# FIX: un solo build con GIT_SHA para trazabilidad
GIT_SHA=$(git rev-parse --short HEAD)
echo ">>> [2/5] Build de imagen — tag: ${GIT_SHA}..."

# FIX: detectar si estamos en SageMaker para usar --network sagemaker
NETWORK_FLAG=""
if [ -n "${SM_CURRENT_HOST:-}" ]; then
    echo "    Detectado entorno SageMaker — usando --network sagemaker"
    NETWORK_FLAG="--network sagemaker"
fi

docker build ${NETWORK_FLAG} \
    --platform linux/amd64 \
    -t "${ECR_URI}:${GIT_SHA}" \
    -t "${ECR_URI}:latest" \
    .

echo ">>> [2/5] Push de imagen..."
docker push "${ECR_URI}:${GIT_SHA}"
docker push "${ECR_URI}:latest"

# ─────────────────────────────────────────────────────────────────────────────
# Paso 3: Obtener VPC y subnets default
# ─────────────────────────────────────────────────────────────────────────────
echo ">>> [3/5] Obteniendo VPC y subnets..."
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query "Vpcs[0].VpcId" \
    --output text --region "${REGION}")

SUBNET_IDS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=${VPC_ID}" "Name=defaultForAz,Values=true" \
    --query "Subnets[*].SubnetId" \
    --output text --region "${REGION}" | tr '\t' ',')

echo "    VPC:     ${VPC_ID}"
echo "    Subnets: ${SUBNET_IDS}"

# ─────────────────────────────────────────────────────────────────────────────
# Paso 4: Desplegar con CloudFormation (un solo stack)
# ─────────────────────────────────────────────────────────────────────────────
echo ">>> [4/5] Desplegando CloudFormation stack: ${STACK_NAME}..."
# FIX: un solo deploy con todos los parámetros requeridos por el YAML corregido
# FIX: ServiceName correcto, no "house-pred"
aws cloudformation deploy \
    --template-file infra/ecs-fargate-app.yaml \
    --stack-name "${STACK_NAME}" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        VpcId="${VPC_ID}" \
        SubnetIds="${SUBNET_IDS}" \
        ImageUri="${ECR_URI}:${GIT_SHA}" \
        ServiceName="${SERVICE_NAME}" \
        DBHostPrimary="${DB_HOST_PRIMARY}" \
        DBHostReplica="${DB_HOST_REPLICA}" \
        RDSSecurityGroupId="${RDS_SG_ID}" \
        SecretArn="${SECRET_ARN}" \
    --region "${REGION}"

# ─────────────────────────────────────────────────────────────────────────────
# Paso 5: Obtener outputs del stack y mostrar URL
# ─────────────────────────────────────────────────────────────────────────────
echo ">>> [5/5] Obteniendo URL de la aplicación..."
APP_URL=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='AppURL'].OutputValue" \
    --output text --region "${REGION}")

ECS_SG_ID=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='ECSSecurityGroupId'].OutputValue" \
    --output text --region "${REGION}")

echo ""
echo "════════════════════════════════════════════"
echo "  Deploy completado"
echo "  App URL:    ${APP_URL}"
echo "  ECS SG ID:  ${ECS_SG_ID}"
echo "════════════════════════════════════════════"
echo ""
echo "SIGUIENTE PASO MANUAL:"
echo "  Agregar el ECS Security Group como inbound rule en el SG de RDS:"
echo ""
echo "  aws ec2 authorize-security-group-ingress \\"
echo "    --group-id ${RDS_SG_ID} \\"
echo "    --protocol tcp \\"
echo "    --port 5432 \\"
echo "    --source-group ${ECS_SG_ID} \\"
echo "    --region ${REGION}"
echo ""
echo "  Sin este paso ECS no puede conectarse a RDS."