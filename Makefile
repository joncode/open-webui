# ============================================================
# Development
# ============================================================

.PHONY: dev dev-frontend dev-backend test test-frontend test-backend lint

## Start both frontend and backend dev servers
dev:
	@make -j2 dev-backend dev-frontend

## Frontend dev server (Vite)
dev-frontend:
	npm run dev

## Backend dev server (uvicorn with CORS for local frontend)
dev-backend:
	cd backend && CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:8080" \
		python3 -m uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --reload

## Run all tests
test: test-frontend test-backend

## Frontend tests (vitest)
test-frontend:
	npm run test:frontend

## Backend tests (pytest) — Jaco tests only (skips upstream integration tests that need Docker/Redis)
test-backend:
	cd backend && python3 -m pytest open_webui/test/utils/

## Backend tests — all (requires Docker, Redis, moto)
test-backend-all:
	cd backend && python3 -m pytest

## Lint everything
lint:
	npm run lint

# ============================================================
# Docker (production)
# ============================================================

ifneq ($(shell which docker-compose 2>/dev/null),)
    DOCKER_COMPOSE := docker-compose
else
    DOCKER_COMPOSE := docker compose
endif

install:
	$(DOCKER_COMPOSE) up -d

remove:
	@chmod +x confirm_remove.sh
	@./confirm_remove.sh

start:
	$(DOCKER_COMPOSE) start
startAndBuild: 
	$(DOCKER_COMPOSE) up -d --build

stop:
	$(DOCKER_COMPOSE) stop

update:
	# Calls the LLM update script
	chmod +x update_ollama_models.sh
	@./update_ollama_models.sh
	@git pull
	$(DOCKER_COMPOSE) down
	# Make sure the ollama-webui container is stopped before rebuilding
	@docker stop open-webui || true
	$(DOCKER_COMPOSE) up --build -d
	$(DOCKER_COMPOSE) start

