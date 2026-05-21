#!/bin/bash
# Configura credenciales AWS para usar el CLI y desplegar en ECS Fargate.
# Cada usuario corre este script con sus propias credenciales.
# Las credenciales se guardan en ~/.aws/credentials (nunca en el repo).

set -euo pipefail

REGION="us-east-1"

echo "════════════════════════════════════════════"
echo "  Configuración de credenciales AWS"
echo "════════════════════════════════════════════"
echo ""
echo "Necesitas tu Access Key ID y Secret Access Key."
echo "Las puedes generar en: AWS Console → IAM → Usuarios → Security credentials"
echo ""

aws configure set region "${REGION}"
aws configure set output json
aws configure

echo ""
echo "Verificando credenciales..."
IDENTITY=$(aws sts get-caller-identity 2>&1) || {
    echo ""
    echo "ERROR: Las credenciales no son válidas o no tienen permisos."
    echo "${IDENTITY}"
    exit 1
}

ACCOUNT=$(echo "${IDENTITY}" | python3 -c "import sys,json; print(json.load(sys.stdin)['Account'])")
USER=$(echo "${IDENTITY}"    | python3 -c "import sys,json; print(json.load(sys.stdin)['Arn'])")

echo ""
echo "════════════════════════════════════════════"
echo "  Autenticación exitosa"
echo "  Cuenta:  ${ACCOUNT}"
echo "  Usuario: ${USER}"
echo "  Región:  ${REGION}"
echo "════════════════════════════════════════════"
