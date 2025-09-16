# Video Storage Platform Makefile

.PHONY: help setup build up down logs clean deploy backup restore test lint format

# Colors
YELLOW := \033[33m
GREEN := \033[32m
RED := \033[31m
RESET := \033[0m

# Default target
help: ## Show this help message
	@echo "$(YELLOW)Video Storage Platform$(RESET)"
	@echo
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Initial setup of the platform
	@echo "$(YELLOW)Setting up Video Storage Platform...$(RESET)"
	@chmod +x scripts/*.sh
	@./scripts/setup.sh

build: ## Build all Docker images
	@echo "$(YELLOW)Building Docker images...$(RESET)"
	@docker-compose build

up: ## Start all services
	@echo "$(YELLOW)Starting all services...$(RESET)"
	@docker-compose up -d

down: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(RESET)"
	@docker-compose down

restart: ## Restart all services
	@echo "$(YELLOW)Restarting all services...$(RESET)"
	@docker-compose restart

logs: ## Show logs from all services
	@docker-compose logs --tail=100 -f

logs-backend: ## Show backend logs
	@docker-compose logs --tail=100 -f backend

logs-frontend: ## Show frontend logs
	@docker-compose logs --tail=100 -f frontend

logs-worker: ## Show worker logs
	@docker-compose logs --tail=100 -f worker

logs-traefik: ## Show Traefik logs
	@docker-compose logs --tail=100 -f traefik

status: ## Show service status
	@docker-compose ps

stats: ## Show system stats
	@./scripts/maintenance.sh stats

clean: ## Clean up Docker resources
	@echo "$(YELLOW)Cleaning up Docker resources...$(RESET)"
	@docker-compose down --volumes
	@docker system prune -f
	@./scripts/maintenance.sh cleanup

deploy: ## Deploy to production
	@echo "$(YELLOW)Deploying to production...$(RESET)"
	@./scripts/deploy.sh

backup: ## Create backup
	@echo "$(YELLOW)Creating backup...$(RESET)"
	@./scripts/maintenance.sh backup

health: ## Run health checks
	@echo "$(YELLOW)Running health checks...$(RESET)"
	@./scripts/maintenance.sh health

monitor: ## Monitor services in real-time
	@./scripts/maintenance.sh monitor

# Development commands
dev-backend: ## Start backend in development mode
	@cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend in development mode
	@cd frontend && npm start

dev-worker: ## Start worker in development mode
	@cd backend && celery -A app.tasks.celery_app worker --loglevel=info

install-backend: ## Install backend dependencies
	@cd backend && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies
	@cd frontend && npm install

# Database commands
db-migrate: ## Run database migrations
	@docker-compose exec backend alembic upgrade head

db-shell: ## Open database shell
	@docker-compose exec postgres psql -U $$POSTGRES_USER -d $$POSTGRES_DB

db-backup: ## Backup database only
	@docker-compose exec postgres pg_dump -U $$POSTGRES_USER $$POSTGRES_DB > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Testing commands
test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	@cd backend && python -m pytest

test-frontend: ## Run frontend tests
	@cd frontend && npm test

# Code quality
lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Run backend linting
	@cd backend && flake8 . && black --check .

lint-frontend: ## Run frontend linting
	@cd frontend && npm run lint

format: ## Format code
	@cd backend && black .
	@cd frontend && npm run format

# SSL commands
ssl-renew: ## Renew SSL certificates
	@./scripts/maintenance.sh ssl-renew

# Security
security-scan: ## Run security scan
	@echo "$(YELLOW)Running security scan...$(RESET)"
	@docker run --rm -v $(PWD):/app -w /app securecodewarrior/docker-security-scanner

# Network
network-create: ## Create external network
	@docker network create web || true

network-remove: ## Remove external network
	@docker network rm web || true

# Environment
env-example: ## Create .env from example
	@cp .env.example .env
	@echo "$(GREEN)Created .env file from template$(RESET)"
	@echo "$(YELLOW)Please edit .env file with your configuration$(RESET)"

# Production helpers
prod-up: network-create ## Start production environment
	@ENV=production docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down: ## Stop production environment
	@ENV=production docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Utility commands
shell-backend: ## Open shell in backend container
	@docker-compose exec backend bash

shell-frontend: ## Open shell in frontend container
	@docker-compose exec frontend sh

shell-worker: ## Open shell in worker container
	@docker-compose exec worker bash

# Quick development setup
dev-setup: install-backend install-frontend build up ## Complete development setup
	@echo "$(GREEN)Development environment ready!$(RESET)"
	@echo "$(YELLOW)Frontend: http://localhost:3000$(RESET)"
	@echo "$(YELLOW)Backend: http://localhost:8000$(RESET)"