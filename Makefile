# Makefile for the project. It defines build and run commands for the application.

APP_IMAGE := auto-repair-shop:latest
ECR_REGION := us-east-1
CODE_PATHS := main.py frontend

.PHONY: help install shell run docker-build docker-run auth create-ecr-repo deploy-fargate run-test format-black format-black-check format-black-list format-ruff format-ruff-check

help:
	@echo "Comandos disponibles:"
	@echo "  make install           - Instala dependencias en el entorno virtual"
	@echo "  make shell             - Abre una shell con .venv activado"
	@echo "  make run               - Ejecuta la app de Streamlit en local"
	@echo "  make docker-build      - Construye la imagen Docker"
	@echo "  make docker-run        - Ejecuta la imagen Docker y valida health"
	@echo "  make auth              - Configura credenciales AWS"
	@echo "  make create-ecr-repo   - Crea repositorio ECR y sube imagen"
	@echo "  make deploy-fargate    - Build, push ECR y despliega en ECS Fargate (AWS)"
	@echo "  make run-test          - Ejecuta pruebas con pytest"
	@echo "  make format-black      - Formatea con black"
	@echo "  make format-black-check- Verifica formato con black"
	@echo "  make format-black-list - Lista archivos con formato pendiente"
	@echo "  make format-ruff       - Formatea con ruff"
	@echo "  make format-ruff-check - Verifica formato con ruff"

install:
	@echo "Creando entorno virtual con Python 3.11..."
	uv venv --python 3.11 --clear
	@echo "Instalando dependencias de la app..."
	uv pip install -r requirements-app.txt

shell:
	@echo "Abriendo shell con entorno virtual activado..."
	@. .venv/bin/activate && exec $$SHELL

run:
	@echo "Iniciando la aplicación Streamlit..."
	@set -a && . ./.env && set +a && .venv/bin/streamlit run frontend/app.py

# docker build
docker-build:
	@echo "Construyendo imagen en Docker..."
	docker build -t $(APP_IMAGE) .

# docker run
docker-run:
	@echo "Ejecutando la aplicación en Docker..."
	@docker rm -f auto-repair-shop-app >/dev/null 2>&1 || true
	@docker run --rm -d --name auto-repair-shop-app -p 8501:8501 \
		--env-file .env \
		-v ~/.aws:/root/.aws:ro \
		$(APP_IMAGE)
	@echo "Aplicación en ejecución en http://localhost:8501"
	@echo "Validando health check..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		curl -fsS http://localhost:8501/_stcore/health >/dev/null && break; \
		sleep 2; \
	done
	@curl -fsS http://localhost:8501/_stcore/health && echo "\nHealth check OK"
	@echo "Mostrando logs del contenedor (Ctrl+C para detener y limpiar)..."
	@trap 'echo ""; echo "Deteniendo contenedor auto-repair-shop-app..."; docker stop auto-repair-shop-app >/dev/null 2>&1 || true; exit 0' INT TERM; \
		docker logs -f auto-repair-shop-app

# auth
auth:
	@bash auth.sh

# deploy ECS Fargate
deploy-fargate:
	@echo "Desplegando en ECS Fargate (build → push ECR → CloudFormation)..."
	@bash infra/build_ecs.sh

# Crea repositorio ECR, autentica y sube imagen
create-ecr-repo:
	@bash -c '\
		set -euo pipefail; \
		echo "Creando repositorio ECR en AWS..."; \
		aws ecr create-repository --repository-name auto-repair-shop --region $(ECR_REGION) 2>/dev/null || true; \
		ACCOUNT_ID=$$(aws sts get-caller-identity --query Account --output text); \
		ECR_URI="$$ACCOUNT_ID.dkr.ecr.$(ECR_REGION).amazonaws.com/auto-repair-shop"; \
		echo "Autenticando en ECR..."; \
		aws ecr get-login-password --region $(ECR_REGION) | \
			docker login --username AWS --password-stdin "$$ACCOUNT_ID.dkr.ecr.$(ECR_REGION).amazonaws.com"; \
		docker tag $(APP_IMAGE) "$$ECR_URI:latest"; \
		docker push "$$ECR_URI:latest"; \
		echo "Imagen subida a: $$ECR_URI:latest"; \
	'

run-test:
	@echo "Ejecutando pruebas con pytest..."
	@uv run --python 3.11 pytest -v; \
	status=$$?; \
	if [ $$status -eq 5 ]; then \
		echo "No se encontraron tests (pytest exit code 5)."; \
		exit 0; \
	fi; \
	exit $$status

# Tarea para formatear código con black
format-black:
	uv run black $(CODE_PATHS)

# Tarea para verificar formato con black sin modificar archivos
format-black-check:
	uv run black --check --diff $(CODE_PATHS)

# Lista solo archivos que necesitan formato (sin diff)
format-black-list:
	uv run black --check $(CODE_PATHS) || true

# Tarea para formatear con ruff
format-ruff:
	uv run ruff format $(CODE_PATHS)

# Tarea para verificar formato con ruff sin modificar archivos
format-ruff-check:
	uv run ruff check --output-format=full $(CODE_PATHS) || true
