# Development setup

Local environment, run the API, test, migrate, and operate PostgreSQL.

---

## Prerequisites

- Python **3.11+**
- Docker with `docker-compose` or `docker compose`
- `make` (optional; wraps common commands)

---

## Getting started

```mermaid
flowchart TD
    A[cp .env.example .env] --> B[make up]
    B --> C[make migrate]
    C --> D[venv + pip install]
    D --> E[uvicorn app.main:app --reload]
    E --> F[make check / open /docs]
```

### 1. Configure

```bash
cp .env.example .env
```

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL (`postgresql+psycopg://...`) |
| `REDIS_URL` | Used only for `GET /ready` |
| `EVENT_HASH_CHAIN` | Optional tamper-evident event chaining |
| `LOG_JSON` | Structured JSON logs when `true` |
| `POSTGRES_PORT` / `REDIS_PORT` | Host port overrides |

### 2. Start infrastructure

```bash
make up          # Postgres + Redis
make migrate     # Alembic upgrade head
```

### 3. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# or: make install
```

### 4. Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

| URL | Purpose |
|-----|---------|
| http://localhost:8000/docs | OpenAPI |
| `GET /health` | Liveness |
| `GET /ready` | Postgres + Redis |

### 5. Tests

```bash
make check       # lint + unit tests (no Docker required for unit)
make test-all    # includes integration (needs Postgres)
```

Integration tests skip automatically when PostgreSQL is unreachable.

---

## Local stack

```mermaid
flowchart LR
    DEV[Developer machine] --> API[uvicorn :8000]
    API --> PG[(Postgres :5432)]
    API --> RD[(Redis :6379 readiness)]
    DEV --> DC[docker compose]
    DC --> PG
    DC --> RD
```

---

## PostgreSQL connection (defaults)

| Setting | Value |
|---------|-------|
| Host | `localhost` |
| Port | `5432` (`POSTGRES_PORT` in `.env`) |
| Database | `workflow_engine` |
| User / password | `workflow` / `workflow` |
| Container | `workflow_engine_postgres` |

```bash
# SQLAlchemy (.env)
DATABASE_URL=postgresql+psycopg://workflow:workflow@localhost:5432/workflow_engine

# psql
postgresql://workflow:workflow@localhost:5432/workflow_engine
```

The app normalizes `postgresql://`, `postgres://`, and `postgresql+asyncpg://` to `postgresql+psycopg://`.

### Port already in use

```bash
POSTGRES_PORT=5433
DATABASE_URL=postgresql+psycopg://workflow:workflow@localhost:5433/workflow_engine
```

Then `make down && make up`.

---

## Docker / Compose

```bash
make up              # start Postgres + Redis (detached)
make down            # stop (keep volumes)
make ps              # status
make logs            # all services
make db-logs         # Postgres only
make db-wait         # wait until pg_isready
```

| Service | Default port |
|---------|--------------|
| Postgres | 5432 |
| Redis | 6379 |

---

## Migrations (Alembic)

```mermaid
flowchart LR
    M[Edit SQLAlchemy models] --> G["make migration msg='…'"]
    G --> R[Review alembic/versions/]
    R --> U[make migrate]
    U --> DB[(Postgres)]
```

```bash
make migrate                              # alembic upgrade head
make migration msg='describe change'      # autogenerate
make migrate-current                      # current revision
make migrate-history                      # list revisions
make migrate-down                         # downgrade -1
```

```bash
alembic downgrade base    # roll back everything
alembic stamp head        # mark migrated without running (careful)
```

Models: `app/infrastructure/persistence/models/`. Schema reference: [DATABASE.md](DATABASE.md).

### Reset database (destructive)

```bash
make db-reset
# or: docker-compose down -v && docker-compose up -d && make db-wait && make migrate
```

### psql

```bash
make db-psql
# or: psql postgresql://workflow:workflow@localhost:5432/workflow_engine
```

```sql
\dt
\d workflow_events
SELECT id, name, status FROM workflow_instances;
```

### Verify connectivity

```bash
make db-wait
curl http://localhost:8000/ready
```

---

## Backup and restore

**Linux / macOS:**

```bash
make db-backup                              # timestamped dump in backups/
make db-backup BACKUP_FILE=backups/my.dump
make db-restore BACKUP_FILE=backups/my.dump
```

**Windows (cmd.exe):**

```bat
db.bat backup
db.bat backup backups\my.dump
db.bat restore backups\my.dump
```

Dumps use `pg_dump -Fc` and are cross-platform.

---

## Development commands

```bash
make install      # pip install -r requirements.txt
make lint         # ruff check
make format       # ruff format
make test         # unit only
make test-all     # unit + integration
make check        # lint + unit
make pre-commit   # git hooks
```

### Testing layout

| Directory | Scope | Needs Postgres |
|-----------|-------|----------------|
| `tests/unit/` | Domain & application logic | No |
| `tests/integration/` | Repositories, API, orchestrator | Yes |
| `tests/fixtures/` | Sample frontend JSON | — |

Mark integration tests with `@pytest.mark.integration`.

---

## Demo workflow (smoke)

Fixtures: `tests/fixtures/`.

```mermaid
flowchart LR
    S([start]) --> G[General Information]
    G --> R[Raw Material Pricing]
    R --> E([end])
```

```mermaid
sequenceDiagram
    participant You
    participant API
    participant DB

    You->>API: POST /definitions/nodes (×2)
    API->>DB: node_definitions + versions
    You->>API: POST /definitions/workflows
    API->>DB: workflow_definitions + version
    You->>API: POST /instances
    API->>DB: instance + node_instances + events
    API-->>You: pending_node_ids
    You->>API: POST .../nodes/{graph_node_id}/submit
    API->>DB: execution + events + projections
    Note over You,API: Repeat submit until COMPLETED
```

```bash
# Publish
curl -X POST http://localhost:8000/api/v1/definitions/nodes \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/node_general_information.json

curl -X POST http://localhost:8000/api/v1/definitions/nodes \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/node_raw_material_pricing.json

curl -X POST http://localhost:8000/api/v1/definitions/workflows \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/workflow_test.json

# Start
curl -X POST http://localhost:8000/api/v1/instances \
  -H 'Content-Type: application/json' \
  -d '{"name": "Demo run", "workflow_definition_id": "1091df5d-58d8-4233-abd5-0a85ec476470"}'

# Submit (use graph node id from pending_node_ids, not definition UUID)
curl -X POST http://localhost:8000/api/v1/instances/{instance_id}/nodes/{workflow_node_id}/submit \
  -H 'Content-Type: application/json' \
  -d '{"outputs": {"customerName": "ACME", "partName": "PART-1", "castingProcess": "GDC", "volume": 10}}'
```

API base path: `/api/v1`. Full OpenAPI: `/docs`.

---

## Related docs

- [Architecture](ARCHITECTURE.md) — folders, class diagram, code flow
- [Database](DATABASE.md) — tables, ER diagram, enums
