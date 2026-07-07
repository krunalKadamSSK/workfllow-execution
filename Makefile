COMPOSE := $(shell command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker compose)
PYTHON ?= python3
POSTGRES_CONTAINER := workflow_engine_postgres
POSTGRES_USER := workflow
POSTGRES_DB := workflow_engine
BACKUP_DIR := backups

.PHONY: up down ps logs install lint format test check pre-commit
.PHONY: migrate migration migrate-down migrate-current migrate-history
.PHONY: db-psql db-logs db-reset db-wait db-restart db-backup db-restore

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
	@until docker exec $(POSTGRES_CONTAINER) pg_isready -U $(POSTGRES_USER) -d $(POSTGRES_DB) >/dev/null 2>&1; do sleep 1; done
	@echo "PostgreSQL is ready."

db-restart:
	$(COMPOSE) down
	$(COMPOSE) up -d postgres
	$(MAKE) db-wait

db-psql:
	docker exec -it $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

db-backup: db-wait
	@mkdir -p $(BACKUP_DIR)
	@backup_file="$(if $(file),$(file),$(BACKUP_DIR)/workflow_engine_$$(date +%Y%m%d_%H%M%S).dump)"; \
	echo "Backing up to $$backup_file..."; \
	docker exec $(POSTGRES_CONTAINER) pg_dump -U $(POSTGRES_USER) -d $(POSTGRES_DB) -Fc -f /tmp/backup.dump; \
	docker cp $(POSTGRES_CONTAINER):/tmp/backup.dump "$$backup_file"; \
	docker exec $(POSTGRES_CONTAINER) rm -f /tmp/backup.dump; \
	echo "Backup complete: $$backup_file"

db-restore:
	@if [ -z "$(file)" ]; then \
		echo "Usage: make db-restore file=path/to/backup.dump"; \
		exit 1; \
	fi
	@if [ ! -f "$(file)" ]; then \
		echo "Backup file not found: $(file)"; \
		exit 1; \
	fi
	@$(MAKE) db-wait
	@echo "Restoring from $(file)..."
	@docker cp "$(file)" $(POSTGRES_CONTAINER):/tmp/backup.dump
	@docker exec $(POSTGRES_CONTAINER) pg_restore -U $(POSTGRES_USER) -d $(POSTGRES_DB) --clean --if-exists /tmp/backup.dump; \
	rc=$$?; \
	docker exec $(POSTGRES_CONTAINER) rm -f /tmp/backup.dump; \
	if [ $$rc -gt 1 ]; then exit $$rc; fi
	@echo "Restore complete."

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
