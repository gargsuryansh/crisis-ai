# =============================================================================
# CrisisAI — Makefile (Docker Workflow Helpers)
# Google Solution Challenge 2026
#
# Usage:
#   make up          — Build and start all services
#   make backend     — Start only the backend
#   make down        — Stop all services
#   make logs        — Tail logs
#   make health      — Hit the health endpoint
#   make clean       — Stop + remove volumes + prune
# =============================================================================

.PHONY: help up backend down logs health shell clean build push test

# Default target
help: ## Show this help
	@echo ""
	@echo "CrisisAI Docker Commands:"
	@echo "────────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Local Development ───────────────────────────────────────────────────────

up: ## Build and start all services (backend + dashboard + proxy)
	docker compose up --build -d
	@echo "\n✅ Stack is up. Backend → http://localhost:8000  |  Proxy → http://localhost:80\n"

backend: ## Start only the backend service (fastest local workflow)
	docker compose up backend --build -d
	@echo "\n✅ Backend is up → http://localhost:8000\n"

down: ## Stop all services
	docker compose down
	@echo "\n🛑 All services stopped.\n"

restart: ## Restart all services
	docker compose restart

logs: ## Tail logs from all services
	docker compose logs -f --tail=100

logs-backend: ## Tail backend logs only
	docker compose logs -f --tail=100 backend

# ── Health & Testing ────────────────────────────────────────────────────────

health: ## Hit the backend health endpoint
	@curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || \
		curl -s http://localhost:8000/health

ws-test: ## Test WebSocket connection (requires websocat or wscat)
	@echo "Testing WebSocket at ws://localhost:8000/api/v1/ws ..."
	@which websocat > /dev/null 2>&1 && \
		echo '{"type":"ping"}' | websocat ws://localhost:8000/api/v1/ws || \
		echo "Install websocat: cargo install websocat  (or use wscat: npx wscat -c ws://localhost:8000/api/v1/ws)"

shell: ## Open a shell inside the running backend container
	docker compose exec backend /bin/bash || docker compose exec backend /bin/sh

# ── Cleanup ─────────────────────────────────────────────────────────────────

clean: ## Stop services, remove volumes, prune images
	docker compose down -v --remove-orphans
	docker image prune -f
	@echo "\n🧹 Cleaned up.\n"

clean-all: ## Nuclear option: remove everything including named volumes
	docker compose down -v --remove-orphans --rmi local
	docker system prune -f
	@echo "\n💥 Full cleanup done.\n"

# ── Production ──────────────────────────────────────────────────────────────

IMAGE_NAME ?= crisisai-backend
IMAGE_TAG  ?= latest
GCR_REGION ?= asia-south1
GCR_PROJECT ?= your-gcp-project-id

build: ## Build backend Docker image for production
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

push: ## Tag and push to Google Artifact Registry
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) \
		$(GCR_REGION)-docker.pkg.dev/$(GCR_PROJECT)/crisisai/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push \
		$(GCR_REGION)-docker.pkg.dev/$(GCR_PROJECT)/crisisai/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "\n📦 Pushed to Artifact Registry.\n"
