COMPOSE := $(shell command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker compose)
PYTHON ?= python3

.PHONY: up down ps logs install lint format test check pre-commit

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
	pytest -q

check: lint test

pre-commit:
	pre-commit run --all-files
