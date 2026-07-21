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
| **[Database](docs/DATABASE.md)** | Tables, FKs, ER diagram, enums, write flow |
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

### Backup & Restore

**Linux / macOS (Makefile):**

```bash
make db-backup                              # timestamped dump in backups/
make db-backup BACKUP_FILE=backups/my.dump  # custom path
make db-restore BACKUP_FILE=backups/my.dump # restore from dump
```

**Windows (cmd.exe):**

```bat
db.bat backup                               # timestamped dump in backups\
db.bat backup backups\my.dump               # custom path
db.bat restore backups\my.dump              # restore from dump
```

Dumps use `pg_dump -Fc` (custom format) and are cross-platform — a backup taken on Windows can be restored on Linux/macOS and vice versa.

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
