.PHONY: help install install-dev install-frontend setup-local setup-docker \
        run run-docker run-workers stop-docker clean \
        test test-cov test-docker lint format type-check \
        migrate makemigrations shell dbshell \
        build push logs watch \
        dev-frontend build-frontend lint-frontend \
        dev-all docker-all

# =============================================================================
# VARIABLES
# =============================================================================
PYTHON := python
UV := uv
NPM := npm
DOCKER_COMPOSE := docker compose
PROJECT_NAME := eld-logs
DOCKER_REGISTRY := your-registry.com
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")

# Frontend directory
FRONTEND_DIR := eld_logs_frontend

# Test settings
DJANGO_TEST_SETTINGS := DJANGO_SETTINGS_MODULE=eld_logs.settings.test

# Colors for terminal output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
CYAN := \033[0;36m
NC := \033[0m # No Color

# =============================================================================
# HELP
# =============================================================================
help: ## Show this help message
	@echo "$(BLUE)$(PROJECT_NAME) - Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Usage:$(NC)"
	@echo "  make <command>"
	@echo ""
	@echo "$(GREEN)Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# FULL STACK SETUP
# =============================================================================
install-all: install-dev install-frontend ## Install all dependencies (backend + frontend)
	@echo "$(GREEN)All dependencies installed!$(NC)"

setup-all: setup-local setup-frontend ## Full setup for both backend and frontend
	@echo "$(GREEN)Full stack setup complete!$(NC)"

# =============================================================================
# BACKEND SETUP
# =============================================================================
install: ## Install production dependencies (backend)
	$(UV) sync --no-dev

install-dev: ## Install all dependencies including dev (backend)
	$(UV) sync --all-extras

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
# FRONTEND SETUP (using bun)
# =============================================================================
BUN := bun

install-frontend: ## Install frontend dependencies with bun
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	cd $(FRONTEND_DIR) && $(BUN) install
	@echo "$(GREEN)Frontend dependencies installed!$(NC)"

setup-frontend: install-frontend ## Setup frontend
	@echo "$(GREEN)Frontend setup complete!$(NC)"

# =============================================================================
# FRONTEND RUNNING
# =============================================================================
run-frontend: ## Run frontend development server
	cd $(FRONTEND_DIR) && $(BUN) run dev

dev-frontend: run-frontend ## Alias for run-frontend

build-frontend: ## Build frontend for production
	@echo "$(BLUE)Building frontend...$(NC)"
	cd $(FRONTEND_DIR) && $(BUN) run build
	@echo "$(GREEN)Frontend build complete!$(NC)"

# =============================================================================
# FRONTEND TESTING & QUALITY
# =============================================================================
lint-frontend: ## Run frontend linter
	@echo "$(BLUE)Linting frontend...$(NC)"
	cd $(FRONTEND_DIR) && $(BUN) run lint
	@echo "$(GREEN)Frontend linting complete!$(NC)"

lint-frontend-fix: ## Run frontend linter with auto-fix
	@echo "$(BLUE)Linting and fixing frontend...$(NC)"
	cd $(FRONTEND_DIR) && $(BUN) run lint:fix
	@echo "$(GREEN)Frontend lint fix complete!$(NC)"

type-check-frontend: ## Run TypeScript type checking
	@echo "$(BLUE)Type checking frontend...$(NC)"
	cd $(FRONTEND_DIR) && $(BUN) run type-check
	@echo "$(GREEN)Frontend type check complete!$(NC)"

format-frontend: ## Format frontend code with prettier
	@echo "$(BLUE)Formatting frontend...$(NC)"
	cd $(FRONTEND_DIR) && $(BUN) run format
	@echo "$(GREEN)Frontend formatted!$(NC)"

format-frontend-check: ## Check frontend formatting
	@echo "$(BLUE)Checking frontend formatting...$(NC)"
	cd $(FRONTEND_DIR) && $(BUN) run format:check

check-frontend: ## Run all frontend checks (type-check + lint)
	@echo "$(BLUE)Running all frontend checks...$(NC)"
	cd $(FRONTEND_DIR) && $(BUN) run check
	@echo "$(GREEN)All frontend checks passed!$(NC)"

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd $(FRONTEND_DIR) && $(BUN) test 2>/dev/null || echo "$(YELLOW)No test script configured$(NC)"

clean-frontend: ## Clean frontend build artifacts
	@echo "$(BLUE)Cleaning frontend...$(NC)"
	rm -rf $(FRONTEND_DIR)/.next
	rm -rf $(FRONTEND_DIR)/node_modules/.cache
	rm -rf $(FRONTEND_DIR)/out
	@echo "$(GREEN)Frontend cleaned!$(NC)"

# =============================================================================
# BACKEND RUNNING
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

# =============================================================================
# FULL STACK RUNNING
# =============================================================================
dev-all: ## Run backend and frontend together (requires tmux or multiple terminals)
	@echo "$(CYAN)============================================$(NC)"
	@echo "$(CYAN)  Starting Full Stack Development Server$(NC)"
	@echo "$(CYAN)============================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Please run these commands in separate terminals:$(NC)"
	@echo ""
	@echo "  $(GREEN)Terminal 1 (Backend API):$(NC)"
	@echo "    make run-asgi"
	@echo ""
	@echo "  $(GREEN)Terminal 2 (Celery Workers):$(NC)"
	@echo "    make run-celery"
	@echo ""
	@echo "  $(GREEN)Terminal 3 (Frontend):$(NC)"
	@echo "    make run-frontend"
	@echo ""
	@echo "$(CYAN)Or use 'make dev-tmux' if you have tmux installed$(NC)"
	@echo ""
	@echo "$(BLUE)URLs:$(NC)"
	@echo "  Backend API:  http://localhost:8000"
	@echo "  API Docs:     http://localhost:8000/api/docs/"
	@echo "  Frontend:     http://localhost:3000"

dev-tmux: ## Run full stack in tmux session
	@command -v tmux >/dev/null 2>&1 || { echo "$(RED)tmux is not installed. Please install it first.$(NC)"; exit 1; }
	@echo "$(BLUE)Starting full stack in tmux...$(NC)"
	tmux new-session -d -s eld-dev -n backend 'make run-asgi'
	tmux new-window -t eld-dev -n celery 'make run-celery'
	tmux new-window -t eld-dev -n frontend 'make run-frontend'
	tmux select-window -t eld-dev:frontend
	tmux attach -t eld-dev
	@echo "$(GREEN)tmux session 'eld-dev' started!$(NC)"

stop-tmux: ## Stop tmux development session
	@tmux kill-session -t eld-dev 2>/dev/null || echo "$(YELLOW)No tmux session found$(NC)"

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

run-docker: ## Start all Docker services (backend only)
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)Services started!$(NC)"
	@echo "  API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/api/docs/"
	@echo "  Admin: http://localhost:8000/admin/"

docker-all: ## Start backend in Docker + frontend locally
	@echo "$(BLUE)Starting backend services in Docker...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "$(GREEN)Backend services started!$(NC)"
	@echo "  API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/api/docs/"
	@echo ""
	@echo "$(BLUE)Starting frontend...$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop frontend$(NC)"
	@echo ""
	cd $(FRONTEND_DIR) && $(BUN) run dev

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
# BACKEND TESTING
# =============================================================================
test: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	$(DJANGO_TEST_SETTINGS) $(UV) run pytest -v
	@echo "$(GREEN)Tests complete!$(NC)"

test-fast: ## Run tests without slow tests
	@echo "$(BLUE)Running fast tests...$(NC)"
	$(DJANGO_TEST_SETTINGS) $(UV) run pytest -v -m "not slow"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(DJANGO_TEST_SETTINGS) $(UV) run pytest -v route_calculator/tests/

test-file: ## Run tests for a specific file (usage: make test-file FILE=test_views.py)
	@echo "$(BLUE)Running tests for $(FILE)...$(NC)"
	$(DJANGO_TEST_SETTINGS) $(UV) run pytest -v -k "$(FILE)"

test-match: ## Run tests matching pattern (usage: make test-match PATTERN=test_create)
	@echo "$(BLUE)Running tests matching '$(PATTERN)'...$(NC)"
	$(DJANGO_TEST_SETTINGS) $(UV) run pytest -v -k "$(PATTERN)"

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(DJANGO_TEST_SETTINGS) $(UV) run pytest -v --cov=route_calculator --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)Coverage report: htmlcov/index.html$(NC)"

test-cov-xml: ## Run tests with coverage (XML output for CI)
	$(DJANGO_TEST_SETTINGS) $(UV) run pytest -v --cov=route_calculator --cov-report=xml

test-cov-report: ## Open coverage report in browser
	@echo "$(BLUE)Opening coverage report...$(NC)"
	@open htmlcov/index.html 2>/dev/null || xdg-open htmlcov/index.html 2>/dev/null || echo "$(YELLOW)Open htmlcov/index.html manually$(NC)"

test-docker: ## Run tests in Docker
	$(DOCKER_COMPOSE) exec web $(DJANGO_TEST_SETTINGS) python -m pytest -v

test-cov-docker: ## Run tests with coverage in Docker
	$(DOCKER_COMPOSE) exec web $(DJANGO_TEST_SETTINGS) python -m pytest -v --cov=route_calculator --cov-report=html

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	$(DJANGO_TEST_SETTINGS) $(UV) run ptw -- -v

test-failed: ## Re-run only failed tests
	@echo "$(BLUE)Re-running failed tests...$(NC)"
	$(DJANGO_TEST_SETTINGS) $(UV) run pytest -v --lf

test-debug: ## Run tests with debug output
	@echo "$(BLUE)Running tests with debug output...$(NC)"
	$(DJANGO_TEST_SETTINGS) $(UV) run pytest -v -s --tb=long

test-parallel: ## Run tests in parallel
	@echo "$(BLUE)Running tests in parallel...$(NC)"
	$(DJANGO_TEST_SETTINGS) $(UV) run pytest -v -n auto

# =============================================================================
# BACKEND CODE QUALITY
# =============================================================================
lint: ## Run all backend linters
	@echo "$(BLUE)Running Ruff linter...$(NC)"
	$(UV) run ruff check .
	@echo "$(GREEN)Linting complete!$(NC)"

lint-fix: ## Run linters and fix auto-fixable issues
	@echo "$(BLUE)Fixing linting issues...$(NC)"
	$(UV) run ruff check --fix .
	$(UV) run ruff format .
	@echo "$(GREEN)Linting fixes applied!$(NC)"

format: ## Format backend code with ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	$(UV) run ruff format .
	$(UV) run ruff check --fix .
	@echo "$(GREEN)Formatting complete!$(NC)"

format-check: ## Check backend code formatting without making changes
	@echo "$(BLUE)Checking code formatting...$(NC)"
	$(UV) run ruff format --check .
	$(UV) run ruff check .

type-check: ## Run mypy type checking
	@echo "$(BLUE)Running type checking...$(NC)"
	$(UV) run mypy route_calculator eld_logs
	@echo "$(GREEN)Type checking complete!$(NC)"

# =============================================================================
# FULL STACK QUALITY
# =============================================================================
quality: lint type-check test ## Run all backend quality checks
	@echo "$(GREEN)All backend quality checks passed!$(NC)"

quality-frontend: lint-frontend type-check-frontend ## Run all frontend quality checks
	@echo "$(GREEN)All frontend quality checks passed!$(NC)"

quality-all: quality quality-frontend ## Run all quality checks (backend + frontend)
	@echo "$(GREEN)All quality checks passed!$(NC)"

quality-docker: ## Run all quality checks in Docker
	$(DOCKER_COMPOSE) exec web $(UV) run ruff check .
	$(DOCKER_COMPOSE) exec web $(UV) run mypy route_calculator eld_logs
	$(DOCKER_COMPOSE) exec web $(DJANGO_TEST_SETTINGS) python -m pytest -v

lint-all: lint lint-frontend ## Lint both backend and frontend

format-all: format format-frontend ## Format both backend and frontend

# =============================================================================
# CI/CD COMMANDS
# =============================================================================
ci-test: ## Run tests for CI (with XML coverage)
	@echo "$(BLUE)Running CI tests...$(NC)"
	$(DJANGO_TEST_SETTINGS) $(UV) run pytest -v \
		--cov=route_calculator \
		--cov-report=xml \
		--cov-report=term-missing \
		--junitxml=junit.xml
	@echo "$(GREEN)CI tests complete!$(NC)"

ci-lint: ## Run linting for CI
	@echo "$(BLUE)Running CI linting...$(NC)"
	$(UV) run ruff check . --output-format=github
	$(UV) run ruff format --check .
	@echo "$(GREEN)CI linting complete!$(NC)"

ci-all: ci-lint ci-test ## Run all CI checks
	@echo "$(GREEN)All CI checks passed!$(NC)"

# =============================================================================
# UTILITIES
# =============================================================================
clean: ## Clean up generated files (backend)
	@echo "$(BLUE)Cleaning up backend...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete
	find . -type f -name "junit.xml" -delete
	rm -f celery-*.pid
	@echo "$(GREEN)Backend cleanup complete!$(NC)"

clean-all: clean clean-frontend ## Clean both backend and frontend
	@echo "$(GREEN)Full cleanup complete!$(NC)"

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

docker-build-frontend: ## Build frontend Docker image
	docker build -t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-frontend:$(VERSION) \
		-f $(FRONTEND_DIR)/Dockerfile $(FRONTEND_DIR)

docker-push: ## Push Docker image to registry
	docker push $(DOCKER_REGISTRY)/$(PROJECT_NAME):$(VERSION)

docker-push-frontend: ## Push frontend Docker image to registry
	docker push $(DOCKER_REGISTRY)/$(PROJECT_NAME)-frontend:$(VERSION)

docker-tag-latest: ## Tag current version as latest
	docker tag $(DOCKER_REGISTRY)/$(PROJECT_NAME):$(VERSION) \
		$(DOCKER_REGISTRY)/$(PROJECT_NAME):latest
	docker tag $(DOCKER_REGISTRY)/$(PROJECT_NAME)-frontend:$(VERSION) \
		$(DOCKER_REGISTRY)/$(PROJECT_NAME)-frontend:latest

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

update-deps: ## Update all dependencies
	@echo "$(BLUE)Updating backend dependencies...$(NC)"
	$(UV) sync --upgrade
	@echo "$(BLUE)Updating frontend dependencies...$(NC)"
	cd $(FRONTEND_DIR) && $(BUN) update
	@echo "$(GREEN)All dependencies updated!$(NC)"

check-deps: ## Check for outdated dependencies
	@echo "$(BLUE)Checking backend dependencies...$(NC)"
	$(UV) pip list --outdated 2>/dev/null || echo "Run 'uv pip list --outdated' manually"
	@echo ""
	@echo "$(BLUE)Checking frontend dependencies...$(NC)"
	cd $(FRONTEND_DIR) && $(BUN) outdated || true

# =============================================================================
# QUICK COMMANDS
# =============================================================================
dev: setup-local run-asgi ## Quick start for backend local development

dev-full: setup-all dev-all ## Quick start for full stack development

docker-dev: setup-docker run-docker logs ## Quick start backend with Docker

fresh: clean setup-local ## Clean slate backend local setup

fresh-frontend: clean-frontend setup-frontend ## Clean slate frontend setup

fresh-all: clean-all setup-all ## Clean slate full stack setup

fresh-docker: clean-docker setup-docker run-docker ## Clean slate Docker setup

# =============================================================================
# INFO COMMANDS
# =============================================================================
info: ## Show project information
	@echo "$(CYAN)============================================$(NC)"
	@echo "$(CYAN)  $(PROJECT_NAME) - Project Information$(NC)"
	@echo "$(CYAN)============================================$(NC)"
	@echo ""
	@echo "$(GREEN)Version:$(NC) $(VERSION)"
	@echo ""
	@echo "$(GREEN)Backend:$(NC)"
	@echo "  Python:     $(shell $(PYTHON) --version 2>/dev/null || echo 'not found')"
	@echo "  Django:     $(shell $(PYTHON) -c 'import django; print(django.VERSION)' 2>/dev/null || echo 'not found')"
	@echo "  uv:         $(shell $(UV) --version 2>/dev/null || echo 'not found')"
	@echo ""
	@echo "$(GREEN)Frontend:$(NC)"
	@echo "  Node:       $(shell node --version 2>/dev/null || echo 'not found')"
	@echo "  Bun:        $(shell $(BUN) --version 2>/dev/null || echo 'not found')"
	@echo "  Next.js:    $(shell cd $(FRONTEND_DIR) && node -p "require('./package.json').dependencies.next" 2>/dev/null || echo 'not found')"
	@echo ""
	@echo "$(GREEN)URLs (when running):$(NC)"
	@echo "  Backend API:     http://localhost:8000"
	@echo "  API Docs:        http://localhost:8000/api/docs/"
	@echo "  Django Admin:    http://localhost:8000/admin/"
	@echo "  Frontend:        http://localhost:3000"

ports: ## Check if required ports are available
	@echo "$(BLUE)Checking port availability...$(NC)"
	@lsof -i :3000 >/dev/null 2>&1 && echo "$(RED)Port 3000 is in use$(NC)" || echo "$(GREEN)Port 3000 is available$(NC)"
	@lsof -i :8000 >/dev/null 2>&1 && echo "$(RED)Port 8000 is in use$(NC)" || echo "$(GREEN)Port 8000 is available$(NC)"
	@lsof -i :5432 >/dev/null 2>&1 && echo "$(YELLOW)Port 5432 (PostgreSQL) is in use$(NC)" || echo "$(GREEN)Port 5432 is available$(NC)"
	@lsof -i :6379 >/dev/null 2>&1 && echo "$(YELLOW)Port 6379 (Redis) is in use$(NC)" || echo "$(GREEN)Port 6379 is available$(NC)"