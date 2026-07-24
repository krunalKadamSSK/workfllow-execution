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
| **[Architecture](docs/ARCHITECTURE.md)** | Folder structure, class diagram, **design patterns**, code flow |
| **[Database](docs/DATABASE.md)** | Tables, FKs, ER diagram, enums |
| **[Development](docs/DEVELOPMENT.md)** | Local setup, migrations, tests, demo curls |

## Development

```bash
make check        # lint + unit tests
make test-all     # includes integration tests (needs Postgres)
make format       # ruff format
```

See [Development setup](docs/DEVELOPMENT.md) for Postgres, backup/restore, and full command list.
