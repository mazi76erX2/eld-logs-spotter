.PHONY: help install install-dev setup-local setup-docker \
        run run-docker run-workers stop-docker clean \
        test test-cov test-docker lint format type-check \
        migrate makemigrations shell dbshell \
        build push logs watch

# =============================================================================
# VARIABLES
# =============================================================================
PYTHON := python
UV := uv
DOCKER_COMPOSE := docker compose
PROJECT_NAME := eld-logs
DOCKER_REGISTRY := your-registry.com
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")

# Colors for terminal output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# =============================================================================
# HELP
# =============================================================================
help: ## Show this help message
	@echo "$(BLUE)$(PROJECT_NAME) - Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Local Development:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# LOCAL SETUP
# =============================================================================
install: ## Install production dependencies
	$(UV) sync --no-dev

install-dev: ## Install all dependencies including dev
	$(UV) sync

setup-local: install-dev ## Full local setup (install deps, create .env, migrate)
	@echo "$(BLUE)Setting up local development environment...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)Created .env file from .env.example$(NC)"; \
		echo "$(YELLOW)Please update .env with your API keys$(NC)"; \
	fi
	@mkdir -p static staticfiles media logs
	$(PYTHON) manage.py migrate
	$(PYTHON) manage.py collectstatic --noinput
	@echo "$(GREEN)Local setup complete!$(NC)"

setup-db-local: ## Setup PostgreSQL locally (requires PostgreSQL installed)
	@echo "$(BLUE)Setting up local PostgreSQL...$(NC)"
	createdb eld_db 2>/dev/null || echo "Database may already exist"
	$(PYTHON) manage.py migrate
	@echo "$(GREEN)Database setup complete!$(NC)"

# =============================================================================
# LOCAL RUNNING
# =============================================================================
run: ## Run Django development server
	$(PYTHON) manage.py runserver 0.0.0.0:8000

run-asgi: ## Run with uvicorn (ASGI mode for WebSockets)
	uvicorn eld_logs.asgi:application --host 0.0.0.0 --port 8000 --reload --reload-dir .

run-prod-local: ## Run with gunicorn + uvicorn workers (production-like)
	gunicorn eld_logs.asgi:application \
		--bind 0.0.0.0:8000 \
		--workers 2 \
		--worker-class uvicorn.workers.UvicornWorker \
		--access-logfile - \
		--error-logfile -

run-celery: ## Run Celery worker
	celery -A eld_logs worker -l INFO -Q default,maps -c 2

run-celery-default: ## Run Celery worker (default queue only)
	celery -A eld_logs worker -l INFO -Q default -c 2

run-celery-maps: ## Run Celery worker (maps queue only)
	celery -A eld_logs worker -l INFO -Q maps -c 1

run-celery-beat: ## Run Celery beat scheduler
	celery -A eld_logs beat -l INFO

run-workers: ## Run all background workers (use with tmux/screen)
	@echo "$(YELLOW)Starting workers in background...$(NC)"
	@echo "$(BLUE)Use 'make stop-workers' to stop$(NC)"
	celery -A eld_logs worker -l INFO -Q default -c 2 --detach --pidfile=celery-default.pid
	celery -A eld_logs worker -l INFO -Q maps -c 1 --detach --pidfile=celery-maps.pid
	celery -A eld_logs beat -l INFO --detach --pidfile=celery-beat.pid
	@echo "$(GREEN)Workers started!$(NC)"

stop-workers: ## Stop background Celery workers
	@echo "$(YELLOW)Stopping workers...$(NC)"
	@if [ -f celery-default.pid ]; then kill `cat celery-default.pid` 2>/dev/null || true; rm -f celery-default.pid; fi
	@if [ -f celery-maps.pid ]; then kill `cat celery-maps.pid` 2>/dev/null || true; rm -f celery-maps.pid; fi
	@if [ -f celery-beat.pid ]; then kill `cat celery-beat.pid` 2>/dev/null || true; rm -f celery-beat.pid; fi
	@echo "$(GREEN)Workers stopped!$(NC)"

run-all: ## Run all services locally (requires multiple terminals or tmux)
	@echo "$(RED)This command requires multiple terminals. Use:$(NC)"
	@echo "  Terminal 1: make run-asgi"
	@echo "  Terminal 2: make run-celery"
	@echo "  Or use: make run-docker"

# =============================================================================
# DOCKER SETUP & RUNNING
# =============================================================================
setup-docker: ## Setup Docker environment
	@echo "$(BLUE)Setting up Docker environment...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)Created .env file$(NC)"; \
	fi
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)Docker setup complete!$(NC)"

build: ## Build Docker images
	$(DOCKER_COMPOSE) build

build-no-cache: ## Build Docker images without cache
	$(DOCKER_COMPOSE) build --no-cache

run-docker: ## Start all Docker services
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)Services started!$(NC)"
	@echo "  API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/api/docs/"
	@echo "  Admin: http://localhost:8000/admin/"

run-docker-attached: ## Start Docker services with logs attached
	$(DOCKER_COMPOSE) up

watch: ## Start Docker with watch mode for live reload
	$(DOCKER_COMPOSE) watch

stop-docker: ## Stop all Docker services
	$(DOCKER_COMPOSE) down

stop-docker-clean: ## Stop Docker and remove volumes
	$(DOCKER_COMPOSE) down -v --remove-orphans

restart-docker: stop-docker run-docker ## Restart all Docker services

logs: ## View Docker logs
	$(DOCKER_COMPOSE) logs -f

logs-web: ## View web service logs
	$(DOCKER_COMPOSE) logs -f web

logs-celery: ## View Celery worker logs
	$(DOCKER_COMPOSE) logs -f celery_worker celery_worker_maps

logs-nginx: ## View Nginx logs
	$(DOCKER_COMPOSE) logs -f nginx

# =============================================================================
# DATABASE
# =============================================================================
migrate: ## Run database migrations
	$(PYTHON) manage.py migrate

migrate-docker: ## Run migrations in Docker
	$(DOCKER_COMPOSE) exec web python manage.py migrate

makemigrations: ## Create new migrations
	$(PYTHON) manage.py makemigrations

makemigrations-docker: ## Create migrations in Docker
	$(DOCKER_COMPOSE) exec web python manage.py makemigrations

shell: ## Open Django shell
	$(PYTHON) manage.py shell

shell-docker: ## Open Django shell in Docker
	$(DOCKER_COMPOSE) exec web python manage.py shell

dbshell: ## Open database shell
	$(PYTHON) manage.py dbshell

dbshell-docker: ## Open database shell in Docker
	$(DOCKER_COMPOSE) exec db psql -U eld_user -d eld_db

createsuperuser: ## Create Django superuser
	$(PYTHON) manage.py createsuperuser

createsuperuser-docker: ## Create superuser in Docker
	$(DOCKER_COMPOSE) exec web python manage.py createsuperuser

# =============================================================================
# TESTING
# =============================================================================
test: ## Run tests
	$(PYTHON) -m pytest -v

test-fast: ## Run tests without slow tests
	$(PYTHON) -m pytest -v -m "not slow"

test-cov: ## Run tests with coverage
	$(PYTHON) -m pytest -v --cov=route_calculator --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)Coverage report: htmlcov/index.html$(NC)"

test-cov-xml: ## Run tests with coverage (XML output for CI)
	$(PYTHON) -m pytest -v --cov=route_calculator --cov-report=xml

test-docker: ## Run tests in Docker
	$(DOCKER_COMPOSE) exec web python -m pytest -v

test-cov-docker: ## Run tests with coverage in Docker
	$(DOCKER_COMPOSE) exec web python -m pytest -v --cov=route_calculator --cov-report=html

test-watch: ## Run tests in watch mode
	$(PYTHON) -m pytest-watch -v

# =============================================================================
# CODE QUALITY
# =============================================================================
lint: ## Run all linters
	@echo "$(BLUE)Running Pylint...$(NC)"
	$(PYTHON) -m pylint route_calculator eld_logs --output-format=colorized || true
	@echo ""
	@echo "$(BLUE)Running Ruff...$(NC)"
	$(PYTHON) -m ruff check .
	@echo ""
	@echo "$(GREEN)Linting complete!$(NC)"

lint-fix: ## Run linters and fix auto-fixable issues
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

format: ## Format code with black and ruff
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

format-check: ## Check code formatting without making changes
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m ruff check .

type-check: ## Run mypy type checking
	$(PYTHON) -m mypy route_calculator eld_logs

quality: lint type-check test ## Run all quality checks

quality-docker: ## Run all quality checks in Docker
	$(DOCKER_COMPOSE) exec web python -m pylint route_calculator eld_logs || true
	$(DOCKER_COMPOSE) exec web python -m ruff check .
	$(DOCKER_COMPOSE) exec web python -m mypy route_calculator eld_logs
	$(DOCKER_COMPOSE) exec web python -m pytest -v

# =============================================================================
# UTILITIES
# =============================================================================
clean: ## Clean up generated files
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete
	rm -f celery-*.pid
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-docker: ## Clean Docker resources
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker system prune -f

collectstatic: ## Collect static files
	$(PYTHON) manage.py collectstatic --noinput

collectstatic-docker: ## Collect static files in Docker
	$(DOCKER_COMPOSE) exec web python manage.py collectstatic --noinput

show-urls: ## Show all URL routes
	$(PYTHON) manage.py show_urls 2>/dev/null || $(PYTHON) manage.py diffsettings

check: ## Run Django system checks
	$(PYTHON) manage.py check

check-deploy: ## Run deployment checks
	$(PYTHON) manage.py check --deploy

# =============================================================================
# DOCKER BUILD & PUSH (for CI/CD)
# =============================================================================
docker-build-prod: ## Build production Docker image
	docker build -t $(DOCKER_REGISTRY)/$(PROJECT_NAME):$(VERSION) \
		--target production \
		-f Dockerfile .

docker-push: ## Push Docker image to registry
	docker push $(DOCKER_REGISTRY)/$(PROJECT_NAME):$(VERSION)

docker-tag-latest: ## Tag current version as latest
	docker tag $(DOCKER_REGISTRY)/$(PROJECT_NAME):$(VERSION) \
		$(DOCKER_REGISTRY)/$(PROJECT_NAME):latest

# =============================================================================
# DEVELOPMENT HELPERS
# =============================================================================
generate-secret: ## Generate a new Django secret key
	@$(PYTHON) -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

init-git-hooks: ## Initialize git hooks for pre-commit
	@echo "$(BLUE)Setting up git hooks...$(NC)"
	@if command -v pre-commit &> /dev/null; then \
		pre-commit install; \
		echo "$(GREEN)Git hooks installed!$(NC)"; \
	else \
		echo "$(YELLOW)pre-commit not installed. Run: pip install pre-commit$(NC)"; \
	fi

# =============================================================================
# QUICK COMMANDS
# =============================================================================
dev: setup-local run-asgi ## Quick start for local development

docker-dev: setup-docker run-docker logs ## Quick start with Docker

fresh: clean setup-local ## Clean slate local setup

fresh-docker: clean-docker setup-docker run-docker ## Clean slate Docker setup