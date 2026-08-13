# Workflow Execution Engine

Python workflow execution engine with **event-sourced** runtime state, **versioned definitions**, and **synchronous** task execution.

**Stack:** FastAPI · SQLAlchemy 2.0 (sync / psycopg3) · PostgreSQL · Redis (readiness only)

**Node types:** `userInput` · `table`

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
| **[Developer Guide](docs/DEVELOPER_GUIDE.md)** | Architecture, runtime flow, full API reference, backups, testing |
| **[Database](docs/DATABASE.md)** | Tables, FKs, ER diagram, enums, migrations, write flow |
| [ADR-001](docs/adr/001-architecture-and-standards.md) | SOLID rules, design patterns, error taxonomy |

## Development

```bash
make check        # lint + unit tests (excludes integration)
make test-all     # all tests (needs Postgres)
make format       # ruff format
make pre-commit   # git hooks
```

Integration tests auto-skip when PostgreSQL is unreachable.

### PostgreSQL

```bash
make up && make migrate    # start DB + apply migrations
make db-psql               # interactive psql shell
make db-reset              # wipe data and re-migrate (destructive)
```

### Backup & restore

**Makefile (Linux / macOS):**

```bash
make db-backup                              # timestamped dump in backups/
make db-backup file=backups/my.dump         # custom path
make db-restore file=backups/my.dump        # restore from dump
```

**HTTP API** (also mounted at `/backups` and `/api/v1/backups`):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/backups` | List backups (paginated) |
| `POST` | `/api/v1/backups` | Create backup |
| `POST` | `/api/v1/backups/{id}/restore` | Restore backup |
| `DELETE` | `/api/v1/backups/{id}` | Delete backup |

Configure via `.env`: `BACKUP_ENABLED`, `BACKUP_ALLOW_RESTORE`, `BACKUP_DEPLOYMENT_MODE` (`docker` \| `local`), etc.

**Windows (cmd.exe):**

```bat
db.bat backup                               # timestamped dump in backups\
db.bat backup backups\my.dump               # custom path
db.bat restore backups\my.dump              # restore from dump
```

Dumps use `pg_dump -Fc` (custom format) and are cross-platform.

Full reference: [Developer Guide — PostgreSQL & backups](docs/DEVELOPER_GUIDE.md#postgresql)

## Services (docker-compose)

| Service  | Default port | Notes |
|----------|--------------|-------|
| Postgres | 5432 | Container: `workflow_engine_postgres` (host network on Linux compose file) |
| Redis    | 6379 | Readiness check only; not used for runtime persistence |

Override ports in `.env` if needed (`POSTGRES_PORT`, `REDIS_URL`).

## Demo workflow

Publish fixtures from `tests/fixtures/`, start an instance, submit tasks in order:

```
start → General Information → Raw Material Pricing → end
```

See the [Developer Guide — Runtime flow](docs/DEVELOPER_GUIDE.md#runtime-flow-demo-workflow) for curl examples.

## Current scope & limitations

This engine is suitable for **local development and integration testing** today. Be aware of the current boundaries:

| Area | Current behavior |
|------|------------------|
| **Authentication** | No built-in auth; endpoints are open unless protected by external infrastructure |
| **Execution model** | Synchronous in the HTTP request thread (no job queue) |
| **Graph topology** | DAGs with parallel branches are supported; concurrent completion of parallel terminal tasks requires care (see Developer Guide) |
| **Optimistic concurrency** | `expected_revision` is supported on mutations but optional |
| **Observability** | Request IDs and optional JSON logging; minimal application-level log statements today |
| **Production hardening** | Rate limits, payload caps, and auth must be added or enforced at the gateway before production deploy |

See the Developer Guide for the full API surface, RFQ revisions, seed-from-instance, export, and reopen/invalidate flows.
