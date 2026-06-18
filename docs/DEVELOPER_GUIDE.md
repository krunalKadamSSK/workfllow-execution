# Developer Guide

This document explains how the workflow execution engine is organized, how data flows through it, and how to run and extend it locally.

## What this project does

The engine runs **versioned workflows** defined as React Flow graphs. Each **task node** references a **node definition** (form schema, formulas, etc.). At runtime:

1. Definitions are published and stored in PostgreSQL.
2. A **workflow instance** is started; node definition versions are **pinned**.
3. Users submit task outputs via the API; the orchestrator runs executors **synchronously** in the request thread.
4. State changes are recorded as an **append-only event log**; **projections** are updated for fast reads.

Execution is **linear and synchronous** — there is no job queue or background worker.

---

## Prerequisites

- Python **3.11+**
- Docker with `docker-compose` or `docker compose`
- `make` (optional, wraps common commands)

---

## Getting started

### 1. Clone and configure

```bash
cp .env.example .env
```

Key variables in `.env`:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection (`postgresql+psycopg://...`) |
| `REDIS_URL` | Used only for `GET /ready` health checks |
| `EVENT_HASH_CHAIN` | Optional tamper-evident event chaining |
| `LOG_JSON` | Structured JSON logs when `true` |

### 2. Start infrastructure

```bash
make up          # Postgres + Redis via docker-compose
make migrate     # apply Alembic migrations
```

### 3. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the API server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: http://localhost:8000/docs
- Health: `GET /health` (liveness), `GET /ready` (DB + Redis)

### 5. Run tests

```bash
make check       # lint + unit tests (no Docker required for unit tests)
make test-all    # includes integration tests (requires Postgres)
```

Integration tests auto-skip when PostgreSQL is unreachable.

---

## PostgreSQL

All runtime data (definitions, instances, events, projections) lives in PostgreSQL. Redis is **not** used for persistence.

### Connection details (default)

| Setting | Value |
|---------|-------|
| Host | `localhost` |
| Port | `5432` (override with `POSTGRES_PORT` in `.env`) |
| Database | `workflow_engine` |
| User | `workflow` |
| Password | `workflow` |
| Container | `workflow_engine_postgres` |

**SQLAlchemy URL** (in `.env`):

```bash
DATABASE_URL=postgresql+psycopg://workflow:workflow@localhost:5432/workflow_engine
```

**psql URL** (no driver suffix):

```bash
postgresql://workflow:workflow@localhost:5432/workflow_engine
```

The app accepts `postgresql://`, `postgres://`, or `postgresql+asyncpg://` and normalizes them to `postgresql+psycopg://` for sync SQLAlchemy.

### Docker — start, stop, status

```bash
make up              # start Postgres + Redis (detached)
make down            # stop containers (keep data volumes)
make ps              # container status
make logs            # tail all service logs
make db-logs         # tail Postgres logs only
```

Equivalent `docker-compose` commands:

```bash
docker-compose up -d
docker-compose down
docker-compose ps
docker-compose logs -f postgres
```

### Port already in use

Edit `.env` and change both the port mapping and connection URL:

```bash
POSTGRES_PORT=5433
DATABASE_URL=postgresql+psycopg://workflow:workflow@localhost:5433/workflow_engine
```

Then restart:

```bash
make down && make up
```

### Connect with psql

Interactive shell inside the container:

```bash
make db-psql
```

Or from the host (if `psql` is installed):

```bash
psql postgresql://workflow:workflow@localhost:5432/workflow_engine
```

Useful `psql` commands once connected:

```sql
\dt                          -- list tables
\d workflow_events           -- describe a table
\q                           -- quit

SELECT id, event_type, sequence_number FROM workflow_events ORDER BY sequence_number LIMIT 10;
SELECT id, name, status FROM workflow_instances;
SELECT slug, latest_version FROM workflow_definitions;
```

### Migrations (Alembic)

Apply all pending migrations:

```bash
make migrate
# equivalent: alembic upgrade head
```

Create a new migration after changing SQLAlchemy models:

```bash
make migration msg='add foo column'
# equivalent: alembic revision --autogenerate -m "add foo column"
```

Inspect migration state:

```bash
make migrate-current    # show current revision
make migrate-history    # list all revisions
alembic heads           # show head revision(s)
```

Roll back one revision:

```bash
make migrate-down
# equivalent: alembic downgrade -1
```

Roll back everything:

```bash
alembic downgrade base
```

Mark DB as migrated without running scripts (use with care):

```bash
alembic stamp head
```

Initial schema: `alembic/versions/001_initial_workflow_schema.py`

### Reset database (wipe all data)

**Destructive** — drops volumes and recreates an empty database, then runs migrations:

```bash
make db-reset
```

Manual equivalent:

```bash
docker-compose down -v          # remove postgres_data volume
docker-compose up -d
make db-wait                    # wait until pg_isready succeeds
make migrate
```

### Verify connectivity

```bash
make db-wait                     # exit 0 when Postgres accepts connections
curl http://localhost:8000/ready # API readiness (Postgres + Redis)
```

One-liner from Python (uses `DATABASE_URL` from `.env`):

```bash
python -c "from app.core.database import check_database_connection; check_database_connection(); print('OK')"
```

### Main tables

| Table | Purpose |
|-------|---------|
| `node_definitions` / `node_definition_versions` | Published node schemas |
| `workflow_definitions` / `workflow_definition_versions` | Published workflow graphs |
| `workflow_instances` / `workflow_node_instances` | Runtime instances |
| `workflow_events` | Append-only event log (source of truth) |
| `workflow_projections` / `workflow_node_projections` | Read models rebuilt from events |
| `workflow_snapshots` | Pinned graph JSON at workflow start |

### Backup and restore (optional)

Dump:

```bash
docker exec workflow_engine_postgres pg_dump -U workflow -d workflow_engine -Fc -f /tmp/backup.dump
docker cp workflow_engine_postgres:/tmp/backup.dump ./backup.dump
```

Restore into a fresh database:

```bash
make db-reset
docker cp ./backup.dump workflow_engine_postgres:/tmp/backup.dump
docker exec workflow_engine_postgres pg_restore -U workflow -d workflow_engine --clean --if-exists /tmp/backup.dump
```

---

## Folder structure

```
workflow_engine/
├── app/                        # Application source
│   ├── main.py                 # FastAPI app, middleware, router registration
│   ├── api/                    # Cross-cutting HTTP concerns
│   │   ├── deps.py             # FastAPI dependencies (DB session)
│   │   ├── errors.py           # Domain exception → HTTP status mapping
│   │   ├── schemas.py          # Shared API error response models
│   │   └── v1/health.py        # /health, /ready
│   ├── core/                   # Config, logging, CORS, middleware, DB session
│   ├── modules/                # Feature routers + request/response DTOs
│   │   ├── definitions/        # Publish & list workflow/node definitions
│   │   └── executions/         # Start instances, submit nodes, pause/resume
│   ├── application/            # Use cases (orchestration, ingest, events)
│   ├── domain/                 # Pure business logic (no FastAPI/SQLAlchemy)
│   └── infrastructure/         # SQLAlchemy models, repositories, Redis
├── alembic/                    # Database migrations
├── docs/                       # Architecture ADRs and this guide
├── tests/
│   ├── unit/                   # Domain & application logic (no I/O)
│   ├── integration/            # DB + API tests (need Postgres)
│   └── fixtures/               # Sample node/workflow JSON from the frontend
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

---

## Layered architecture

Dependencies point **inward**. Outer layers call inner layers; the domain never imports from API or infrastructure.

```
┌─────────────────────────────────────────────────────────┐
│  modules/          FastAPI routers + Pydantic DTOs      │
├─────────────────────────────────────────────────────────┤
│  api/              Exception handlers, shared HTTP      │
├─────────────────────────────────────────────────────────┤
│  application/      Orchestrator, ingest, event store    │
├─────────────────────────────────────────────────────────┤
│  domain/           Graph, state machines, executors,    │
│                    validation, ports (protocols)        │
├─────────────────────────────────────────────────────────┤
│  infrastructure/   SQLAlchemy models & repositories    │
└─────────────────────────────────────────────────────────┘
```

| Layer | Responsibility | Examples |
|-------|----------------|----------|
| **modules** | HTTP boundary — validate input, map responses | `definitions/router.py`, `executions/schemas.py` |
| **application** | Coordinate use cases | `WorkflowOrchestrator`, `DefinitionIngestService`, `EventStore` |
| **domain** | Rules and algorithms with no I/O | `WorkflowGraph`, `UserInputExecutor`, `WorkflowStateMachine` |
| **infrastructure** | Persistence and external systems | `DefinitionRepository`, SQLAlchemy models |

See also [ADR-001](adr/001-architecture-and-standards.md) for SOLID mapping and design patterns.

---

## Code structure by concern

### Definitions (`app/modules/definitions` + `app/application/definitions`)

- **Ingest** — `DefinitionIngestService` validates workflow graphs and stores versioned definitions.
- **Validation** — `app/domain/validation/` checks topology, node references, and upstream input wiring.
- **Schemas** — `modules/definitions/schemas/` mirrors the React Flow JSON shape.

### Executions (`app/modules/executions` + `app/application/executions`)

- **Facade** — `ExecutionService.from_session(session)` wires repositories, event store, and orchestrator.
- **Orchestrator** — `WorkflowOrchestrator` is the mediator: start, submit, pause, resume, cancel, advance.
- **Scheduler** — `GraphScheduler` finds ready task nodes from graph topology + node statuses.
- **Input binding** — `GraphInputBinder` + `UpstreamInputResolver` fill locked upstream fields from projections.

### Event sourcing (`app/application/events` + `app/domain/events`)

- **EventStore.append()** — writes `WorkflowEvent` rows and dispatches handlers.
- **Handlers** — update `WorkflowProjection`, `WorkflowNodeProjection`, and snapshots.
- **Rebuilder** — `ProjectionRebuilder` replays the log to rebuild projections from scratch.

### Node executors (`app/domain/executors`)

- **Registry** — `create_default_registry()` maps `baseKind` → executor (currently `userInput` only).
- **Template method** — `BaseNodeExecutor`: resolve upstream defaults → validate fields → persist submitted outputs (formulas run in React)
- **Ports** — `app/domain/ports/executors.py` defines `NodeExecutor`, `ExecutionContext`.

### Persistence (`app/infrastructure/db`)

- **Models** — `definitions`, `instances`, `events`, `projections` tables.
- **Repositories** — one per aggregate; no business logic inside repositories.
- **UnitOfWork** — optional transaction boundary for multi-repo operations.

---

## Runtime flow (demo workflow)

The fixtures in `tests/fixtures/` model a simple pipeline:

```
start → General Information → Raw Material Pricing → end
```

### Step 1 — Publish definitions

```bash
curl -X POST http://localhost:8000/api/v1/definitions/nodes \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/node_general_information.json

curl -X POST http://localhost:8000/api/v1/definitions/nodes \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/node_raw_material_pricing.json

curl -X POST http://localhost:8000/api/v1/definitions/workflows \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/workflow_test.json
```

### Step 2 — Start an instance

```bash
curl -X POST http://localhost:8000/api/v1/instances \
  -H 'Content-Type: application/json' \
  -d '{"name": "Demo run", "workflow_definition_id": "1091df5d-58d8-4233-abd5-0a85ec476470"}'
```

Response includes `pending_node_ids` — graph node IDs ready for submit.

### Step 3 — Submit task outputs

Use the graph node id (e.g. `c24086be-e3d1-4953-8bbf-6b696b8fdd8e`), **not** the node definition UUID:

```bash
curl -X POST http://localhost:8000/api/v1/instances/{instance_id}/nodes/{workflow_node_id}/submit \
  -H 'Content-Type: application/json' \
  -d '{"outputs": {"customerName": "ACME", "partName": "PART-1", "castingProcess": "GDC", "volume": 10}}'
```

Submit the second task when it appears in `pending_node_ids`. When all tasks complete, status becomes `COMPLETED`.

### Step 4 — Inspect state and events

```bash
curl http://localhost:8000/api/v1/instances/{instance_id}
curl http://localhost:8000/api/v1/instances/{instance_id}/events
```

---

## Important concepts

### Graph node id vs node definition id

| ID type | Example | Used for |
|---------|---------|----------|
| **Graph node id** | `c24086be-e3d1-4953-8bbf-6b696b8fdd8e` | API submit path, edges, upstream wiring |
| **Node definition id** | `4eb5cfe4-8eff-463a-a315-a39f31a26756` | Published form schema, pinned at instance creation |

### Node statuses

`WAITING` → `PENDING` (ready for user) → `RUNNING` → `COMPLETED`

A node is submittable only when `PENDING`. Submitting too early returns `409 UPSTREAM_NOT_READY`.

### Upstream inputs

Task nodes can declare `inputs[].source.kind = "upstream"`. Values are read from completed upstream node projections and merged into the executor context. Locked inputs cannot be overridden by the user.

### Event log vs projections

| Store | Role |
|-------|------|
| `workflow_events` | Source of truth — append-only audit trail |
| `workflow_projections` / `workflow_node_projections` | Read models rebuilt from events |

---

## API reference (summary)

Base path: `/api/v1`

### Definitions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/definitions/nodes` | Publish node definition |
| `GET` | `/definitions/nodes` | List node summaries |
| `GET` | `/definitions/nodes/{slug}` | Get node (+ version) |
| `POST` | `/definitions/workflows` | Publish workflow |
| `GET` | `/definitions/workflows` | List workflow summaries |
| `GET` | `/definitions/workflows/{slug}` | Get workflow (+ version) |

### Instances

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/instances` | Start workflow instance |
| `GET` | `/instances/{id}` | Instance + nodes + projection |
| `POST` | `/instances/{id}/nodes/{workflow_node_id}/submit` | Submit task outputs |
| `POST` | `/instances/{id}/pause` | Pause workflow |
| `POST` | `/instances/{id}/resume` | Resume workflow |
| `POST` | `/instances/{id}/cancel` | Cancel workflow |
| `GET` | `/instances/{id}/events` | Event audit trail |

### Error responses

All errors share this shape:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Human-readable summary",
    "details": [],
    "request_id": "uuid-from-X-Request-ID"
  }
}
```

---

## Where to change what

| Task | Start here |
|------|------------|
| Add API endpoint | `app/modules/<feature>/router.py` |
| Add request/response DTO | `app/modules/<feature>/schemas.py` |
| Change orchestration logic | `app/application/executions/orchestrator.py` |
| Add node type (`baseKind`) | `app/domain/executors/` + register in `registry.py` |
| Add validation rule | `app/domain/validation/` |
| Add event type / handler | `app/domain/events/` + `app/application/events/handlers/` |
| Change DB schema | SQLAlchemy model → `alembic revision` → `make migrate` |
| Map new domain error to HTTP | `app/api/errors.py` |

---

## Testing conventions

| Directory | Scope | Requires Postgres |
|-----------|-------|-------------------|
| `tests/unit/` | Pure domain/application logic | No |
| `tests/integration/` | Repositories, orchestrator, API | Yes |
| `tests/fixtures/` | Realistic JSON from the frontend | — |

Mark integration tests with `@pytest.mark.integration`. Use the `api_client` fixture in `tests/conftest.py` for HTTP tests with a rolled-back DB transaction.

---

## Development commands

```bash
make install      # pip install dependencies
make lint         # ruff check
make format       # ruff format
make test         # unit tests only
make test-all     # all tests (requires Postgres)
make check        # lint + unit tests
make pre-commit   # run git hooks
```

### PostgreSQL shortcuts

```bash
make up               # start Postgres + Redis
make migrate          # alembic upgrade head
make migration msg='describe change'   # autogenerate migration
make migrate-current  # show current revision
make migrate-history  # list revisions
make migrate-down     # rollback one revision
make db-psql          # open psql shell
make db-logs          # tail Postgres logs
make db-wait          # wait until Postgres is ready
make db-reset         # wipe volumes + migrate (destructive)
```

See [PostgreSQL](#postgresql) above for full details (connection URLs, backup, table reference).

---

## Extending the engine

To add a new node type (e.g. `apiCall`):

1. Implement `NodeExecutor` in `app/domain/executors/`.
2. Register it in `create_default_registry()` (`app/domain/executors/registry.py`).
3. Add Pydantic schema validation for the definition JSON if needed.
4. Add unit tests for the executor; integration test through the orchestrator.

The orchestrator and API do not need changes if the executor honors the existing `ExecutionContext` contract.

---

## Further reading

- [ADR-001: Architecture and standards](adr/001-architecture-and-standards.md)
- OpenAPI docs at `/docs` when the server is running
- Sample workflow: `tests/fixtures/workflow_test.json`
