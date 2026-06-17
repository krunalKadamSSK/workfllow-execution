# Workflow Execution Engine

Python workflow execution engine using PostgreSQL, Redis, and SQLAlchemy.

## Prerequisites

- Python 3.11+
- Docker with **docker-compose** (standalone) or **docker compose** (v2 plugin)

> **Docker Compose command:** this machine uses the standalone `docker-compose` binary (snap), not the `docker compose` v2 plugin. Use `docker-compose` (with a hyphen), or run `make up`.

## Local setup

```bash
# 1. Environment
cp .env.example .env

# 2. Start Postgres + Redis
docker-compose up -d

# 3. Python virtualenv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Port conflicts

If Redis or Postgres ports are already in use, set alternate ports in `.env`:

```bash
REDIS_PORT=6380
REDIS_URL=redis://localhost:6380/0
```

Then restart: `docker-compose up -d`

## Docker commands

```bash
docker-compose up -d          # start services (or: make up)
docker-compose ps             # check status
docker-compose logs -f        # tail logs
docker-compose down           # stop services
docker-compose down -v        # stop and remove volumes
```

### Install docker compose v2 plugin (optional)

If you prefer `docker compose` (space, no hyphen):

```bash
sudo apt install docker-compose-v2
```

## Services

| Service  | Port | Connection |
|----------|------|------------|
| Postgres | 5432 | `postgresql+asyncpg://workflow:workflow@localhost:5432/workflow_engine` |
| Redis    | 6379 | `redis://localhost:6379/0` |
