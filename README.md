# Workflow Execution Engine

Python workflow execution engine with **event-sourced** runtime state, **versioned definitions**, and **synchronous** task execution.

**Stack:** FastAPI · SQLAlchemy 2.0 (sync) · PostgreSQL · Redis (readiness only)

## Quick start

```bash
cp .env.example .env
make up && make migrate

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- `GET /health` — liveness
- `GET /ready` — PostgreSQL + Redis reachable

## Documentation

| Doc | Contents |
|-----|----------|
| **[Developer Guide](docs/DEVELOPER_GUIDE.md)** | Folder structure, architecture, runtime flow, API summary, where to change what |
| [ADR-001](docs/adr/001-architecture-and-standards.md) | SOLID rules, design patterns, error taxonomy |

## Development

```bash
make check        # lint + unit tests
make test-all     # includes integration tests (needs Postgres)
make format       # ruff format
make pre-commit   # git hooks
```

### PostgreSQL

```bash
make up && make migrate    # start DB + apply migrations
make db-psql               # interactive psql shell
make db-reset              # wipe data and re-migrate (destructive)
```

Full reference: [docs/DEVELOPER_GUIDE.md — PostgreSQL](docs/DEVELOPER_GUIDE.md#postgresql)

## Services (docker-compose)

| Service  | Default port |
|----------|--------------|
| Postgres | 5432 |
| Redis    | 6379 |

Override ports in `.env` if needed (`POSTGRES_PORT`, `REDIS_PORT`).

## Demo workflow

Publish fixtures from `tests/fixtures/`, start an instance, submit tasks in order:

```
start → General Information → Raw Material Pricing → end
```

See the [Developer Guide — Runtime flow](docs/DEVELOPER_GUIDE.md#runtime-flow-demo-workflow) for curl examples.
