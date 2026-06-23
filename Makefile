COMPOSE := $(shell command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker compose)
PYTHON ?= python3
POSTGRES_CONTAINER := workflow_engine_postgres

.PHONY: up down ps logs install lint format test check pre-commit
.PHONY: migrate migration migrate-down migrate-current migrate-history
.PHONY: db-psql db-logs db-reset db-wait db-restart

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

install:
	$(PYTHON) -m pip install -r requirements.txt

lint:
	ruff check app tests

format:
	ruff format app tests

test:
	pytest -q -m "not integration"

test-all:
	pytest -q

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(msg)"

migrate-down:
	alembic downgrade -1

migrate-current:
	alembic current

migrate-history:
	alembic history -v

db-wait:
	@echo "Waiting for PostgreSQL..."
	@until docker exec $(POSTGRES_CONTAINER) pg_isready -U workflow -d workflow_engine >/dev/null 2>&1; do sleep 1; done
	@echo "PostgreSQL is ready."

db-restart:
	$(COMPOSE) down
	$(COMPOSE) up -d postgres
	$(MAKE) db-wait

db-psql:
	docker exec -it $(POSTGRES_CONTAINER) psql -U workflow -d workflow_engine

db-logs:
	$(COMPOSE) logs -f postgres

db-reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d
	$(MAKE) db-wait
	$(MAKE) migrate

check: lint test

pre-commit:
	pre-commit run --all-files
