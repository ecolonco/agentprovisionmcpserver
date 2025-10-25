# ============================================
# MCP Server - Makefile
# ============================================

.PHONY: help install dev test clean docker-up docker-down docker-logs seed migrate

help:
	@echo "MCP Server - Available Commands:"
	@echo ""
	@echo "  make install       - Install dependencies"
	@echo "  make dev          - Run development server"
	@echo "  make test         - Run tests"
	@echo "  make docker-up    - Start Docker Compose services"
	@echo "  make docker-down  - Stop Docker Compose services"
	@echo "  make docker-logs  - Follow Docker logs"
	@echo "  make seed         - Seed database with sample data"
	@echo "  make migrate      - Run database migrations"
	@echo "  make clean        - Clean temporary files"
	@echo ""

# ============================================
# Local Development
# ============================================

install:
	pip install -r requirements.txt

dev:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest --cov=src --cov-report=html --cov-report=term

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

# ============================================
# Docker
# ============================================

docker-up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Services started! Access API at http://localhost:8000/docs"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f mcp-server

docker-rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

# ============================================
# Database
# ============================================

seed:
	python -m scripts.seed_db

migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-rollback:
	alembic downgrade -1

# ============================================
# Code Quality
# ============================================

format:
	black src/ scripts/
	isort src/ scripts/

lint:
	flake8 src/ scripts/
	mypy src/

# ============================================
# Terraform
# ============================================

tf-init:
	cd terraform && terraform init

tf-plan:
	cd terraform && terraform plan

tf-apply:
	cd terraform && terraform apply

tf-destroy:
	cd terraform && terraform destroy
