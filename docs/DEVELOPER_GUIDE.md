# Developer Guide

This document explains how the workflow execution engine is organized, how data flows through it, and how to run and extend it locally.

## What this project does

The engine runs **versioned workflows** defined as React Flow graphs. Each **task node** references a **node definition** (form schema, table config, formulas, etc.). At runtime:

1. Definitions are published and stored in PostgreSQL.
2. A **workflow instance** is started; workflow and node definition versions are **pinned**.
3. Users submit task outputs via the API; the orchestrator runs executors **synchronously** in the request thread.
4. State changes are recorded as an **append-only event log**; **projections** are updated in the same DB transaction for fast reads.

Execution is **synchronous** — there is no job queue or background worker. Long-running validation or large payloads block the HTTP response and hold a DB connection until `session.commit()`.

**Supported node kinds (`baseKind`):** `userInput`, `table`

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
| `EVENT_HASH_CHAIN` | Optional tamper-evident event chaining (`false` by default) |
| `LOG_JSON` | Structured JSON logs when `true` |
| `BACKUP_ENABLED` | Enable backup HTTP API and operations |
| `BACKUP_ALLOW_RESTORE` | Allow restore endpoints (default `true`; set `false` in production unless intentional) |
| `BACKUP_DEPLOYMENT_MODE` | `docker` (pg_dump via container) or `local` (host tools) |
| `CORS_ORIGINS` | Allowed browser origins |

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
make check       # lint + unit tests (no Postgres required)
make test-all    # includes integration tests (requires Postgres)
```

Integration tests auto-skip when PostgreSQL is unreachable.

---

## Security & production notes

**There is no built-in authentication or authorization.** All API routes are open to any caller that can reach the service. For production:

- Place the API behind an authenticated gateway, VPN, or mTLS.
- Treat backup restore and bulk export as **admin-only** operations.
- Set `BACKUP_ALLOW_RESTORE=false` unless restore is explicitly required.
- Send `expected_revision` on mutating instance calls to avoid lost updates.
- Do not run `pg_restore --clean` against a database while the app is serving writes.

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

The app accepts `postgresql://`, `postgres://`, or `postgresql+asyncpg://` and normalizes them to `postgresql+psycopg://` for sync SQLAlchemy.

**Connection pool (defaults):** `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, connect timeout 5s.

### Docker — start, stop, status

```bash
make up              # start Postgres + Redis (detached)
make down            # stop containers (keep data volumes)
make ps              # container status
make logs            # tail all service logs
make db-logs         # tail Postgres logs only
```

### Connect with psql

```bash
make db-psql
```

Useful queries:

```sql
SELECT id, event_type, sequence_number FROM workflow_events ORDER BY sequence_number LIMIT 10;
SELECT id, name, status, rfq_id, current_revision FROM workflow_instances;
SELECT slug, latest_version FROM workflow_definitions;
```

### Migrations (Alembic)

```bash
make migrate                              # alembic upgrade head
make migration msg='add foo column'     # autogenerate
make migrate-current
make migrate-history
make migrate-down                         # downgrade -1
```

Migration chain:

| Revision | Summary |
|----------|---------|
| `4a780231d1ef` | Initial schema |
| `002` | `base_types` catalog |
| `003` | `table` base kind |
| `004` | Base types seed sync |
| `005` | `instance_metadata`, `rfq_id`, `seed_defaults_json` |
| `006` | List/search indexes |

### Reset database (destructive)

```bash
make db-reset
```

### Verify connectivity

```bash
make db-wait
curl http://localhost:8000/ready
python -c "from app.core.database import check_database_connection; check_database_connection(); print('OK')"
```

### Backup and restore

**Makefile:**

```bash
make db-backup                    # backups/workflow_engine_YYYYMMDD_HHMMSS.dump
make db-backup file=backups/my.dump
make db-restore file=backups/my.dump
```

**HTTP API** (`/api/v1/backups`, alias `/backups`):

```bash
curl http://localhost:8000/api/v1/backups
curl -X POST http://localhost:8000/api/v1/backups
curl -X POST http://localhost:8000/api/v1/backups/{backup_id}/restore
curl -X DELETE http://localhost:8000/api/v1/backups/{backup_id}
```

Implementation: `app/patterns/backups/` (Strategy + Repository). Docker mode streams `pg_dump`/`pg_restore` via container exec without writing to container `/tmp`.

**Windows:** `db.bat backup` / `db.bat restore`

See also [DATABASE.md](DATABASE.md) for schema-level write flows.

---

## Folder structure

```
workfllow-execution/
├── app/
│   ├── main.py                 # FastAPI app, middleware, router registration
│   ├── api/
│   │   ├── deps.py             # DB session dependency
│   │   ├── errors.py           # Domain exception → HTTP mapping
│   │   ├── controllers/        # HTTP controllers (backups)
│   │   └── v1/health.py        # /health, /ready
│   ├── core/                   # Config, logging, CORS, middleware, DB engine
│   ├── modules/
│   │   ├── definitions/        # Definition publish & list routes
│   │   ├── executions/         # Instance lifecycle routes
│   │   └── backups/            # Backup HTTP routes
│   ├── application/
│   │   ├── definitions/        # DefinitionIngestService
│   │   ├── executions/         # Orchestrator, scheduler, export, seed memento
│   │   ├── events/             # EventStore, handlers, ProjectionRebuilder
│   │   └── backups/            # BackupService facade
│   ├── domain/                 # Graph, executors, validation, state machines, ports
│   ├── infrastructure/       # SQLAlchemy models, repositories, projection readers
│   └── patterns/backups/       # Backup strategy, command runner, repository
├── alembic/
├── docs/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

---

## Layered architecture

Dependencies point **inward**. Outer layers call inner layers; the domain never imports FastAPI or SQLAlchemy.

```
┌─────────────────────────────────────────────────────────┐
│  modules/          FastAPI routers + Pydantic DTOs      │
├─────────────────────────────────────────────────────────┤
│  api/              Exception handlers, shared HTTP      │
├─────────────────────────────────────────────────────────┤
│  application/      Orchestrator, ingest, event store    │
├─────────────────────────────────────────────────────────┤
│  domain/           Graph, state machines, executors     │
├─────────────────────────────────────────────────────────┤
│  infrastructure/   SQLAlchemy models & repositories     │
└─────────────────────────────────────────────────────────┘
```

See [ADR-001](adr/001-architecture-and-standards.md) for SOLID mapping and design patterns.

---

## Code structure by concern

### Definitions

- **Ingest** — `DefinitionIngestService` validates workflow graphs and stores versioned definitions.
- **Validation** — topology, node references, upstream/metadata input wiring (`app/domain/validation/`).
- **Publish** — re-publish by id creates a new version row and bumps `latest_version`.

### Executions

- **Facade** — `ExecutionService.from_session(session)` wires repositories, event store, orchestrator.
- **Orchestrator** — `WorkflowOrchestrator`: start, submit, pause, resume, cancel, reopen, advance, export.
- **Scheduler** — `GraphScheduler`: ready tasks, downstream invalidation, next pending task.
- **Input binding** — `GraphInputBinder` + `UpstreamInputResolver` (upstream outputs + instance metadata).
- **Seed memento** — `seed_from_instance_id` copies static field defaults from a prior instance (same workflow definition).
- **Export** — Excel export per instance or all instances (`openpyxl`).

### Event sourcing

- **EventStore.append()** — assigns sequence number, optional hash chain, persists event, dispatches handlers.
- **Handlers** — workflow projection, node projection, workflow snapshot on start.
- **ProjectionRebuilder** — deletes projections and replays events (available in tests / `UnitOfWork`; no public API yet).

### Node executors

| `baseKind` | Class | Notes |
|------------|-------|-------|
| `userInput` | `UserInputExecutor` | Synapse form fields; locked upstream validation |
| `table` | `TableExecutor` | Header fields + rows; server-side aggregations |

Registry: `create_default_registry()` in `app/domain/executors/registry.py`.

Lifecycle (`BaseNodeExecutor`): `prepare` → merge outputs → `validate_outputs` → `complete`.

### Transactions

Mutating routes call service methods then **`session.commit()`** explicitly. The `get_db()` dependency rolls back on exception but does **not** auto-commit. Read routes leave the session open until the request ends (implicit read transaction).

---

## Runtime flow (demo workflow)

Fixtures in `tests/fixtures/` — linear pipeline:

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
  -d '{
    "name": "Demo run",
    "workflow_definition_id": "1091df5d-58d8-4233-abd5-0a85ec476470",
    "metadata": {"rfqId": "RFQ-2026-0001", "estimateRevision": "1"}
  }'
```

Optional fields on start:

| Field | Purpose |
|-------|---------|
| `version` | Pin specific workflow definition version (default: latest) |
| `metadata` | Stored in `instance_metadata` / indexed `rfq_id` |
| `seed_from_instance_id` | Copy static defaults from prior instance (same workflow definition) |
| `created_by` | Audit string (client-supplied; not authenticated) |

Response includes `pending_node_ids`, `pending_node_forms`, `next_task_id`, `execution_summary`, `total_cost`.

### Step 3 — Submit task outputs

Use the **graph node id** (e.g. `c24086be-e3d1-4953-8bbf-6b696b8fdd8e`), not the node definition UUID:

```bash
curl -X POST http://localhost:8000/api/v1/instances/{instance_id}/nodes/{workflow_node_id}/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "outputs": {"customerName": "ACME", "partName": "PART-1", "castingProcess": "GDC", "volume": 10},
    "expected_revision": 1
  }'
```

Submit when the node is `PENDING`. Early submit returns `409 UPSTREAM_NOT_READY`.

When all tasks complete, status becomes `COMPLETED` and `total_cost` reflects summed cost contributions.

### Step 4 — Inspect state

```bash
curl http://localhost:8000/api/v1/instances/{instance_id}
curl http://localhost:8000/api/v1/instances/{instance_id}/events
curl http://localhost:8000/api/v1/instances/{instance_id}/node-executions
curl http://localhost:8000/api/v1/instances/{instance_id}/export   # Excel download
```

### RFQ revisions

```bash
# List all instances for an RFQ
curl 'http://localhost:8000/api/v1/instances?rfqId=RFQ-2026-0001'

# Incomplete only
curl 'http://localhost:8000/api/v1/instances?rfqId=RFQ-2026-0001&incompleteOnly=true'

# Check if any incomplete revision exists
curl http://localhost:8000/api/v1/instances/rfq/RFQ-2026-0001/incomplete
```

### Reopen / invalidate (correction flow)

```bash
curl -X POST http://localhost:8000/api/v1/instances/{instance_id}/nodes/{workflow_node_id}/invalidate \
  -H 'Content-Type: application/json' \
  -d '{"reason": "correction", "expected_revision": 3, "reopen_target": true}'
```

- Reopens target task (if completed) and invalidates downstream tasks.
- Completed workflows transition back to `RUNNING`.
- Downstream projections cleared; `currentTotal` recalculated.

---

## Important concepts

### Graph node id vs node definition id

| ID type | Example | Used for |
|---------|---------|----------|
| **Graph node id** | `c24086be-e3d1-4953-8bbf-6b696b8fdd8e` | Submit path, edges, upstream wiring |
| **Node definition id** | `4eb5cfe4-8eff-463a-a315-a39f31a26756` | Published schema, pinned at instance creation |

### Node statuses

```
WAITING → PENDING → RUNNING → COMPLETED
                ↘ INVALIDATED ↗
                ↘ FAILED (supported; not emitted by orchestrator today)
```

Submit is allowed only when `PENDING`.

### Workflow graph topology

Graphs must be **DAGs** (one start, ≥1 end, no cycles). **Parallel branches** (fork/join) are valid — see `tests/unit/test_workflow_graph.py`.

> **Concurrency note:** If two parallel terminal tasks are submitted at exactly the same time, completion detection can race: both transactions may fail to emit `WORKFLOW_COMPLETED`, leaving the workflow in `RUNNING` with all tasks `COMPLETED`. Calling `POST .../resume` triggers `_advance()` and can recover. Prefer serializing terminal submits or fixing with row-level locking before production use with parallel graphs.

### Upstream inputs

`inputs[].source.kind = "upstream"` — values from completed upstream **node projections**. Locked inputs cannot be overridden.

### Metadata inputs

`inputs[].source.kind = "metadata"` — values from `instance_metadata`.

System keys: `rfqId`, `estimateRevision`, `estimatedBy`, `runName`, `currentTotal`. Custom keys must appear in workflow `metadataFields`.

`currentTotal` is mirrored from the workflow projection total after completions and invalidations (used for metadata bindings).

### Event log vs projections

| Store | Role |
|-------|------|
| `workflow_events` | Source of truth — append-only audit trail |
| `workflow_projections` / `workflow_node_projections` | Read models updated synchronously from events |

Under concurrent writes to the same workflow, the aggregate workflow projection JSON can suffer lost updates; node-level projection rows are per-node. `ProjectionRebuilder` can replay events to rebuild (operational tooling only today).

### Optimistic concurrency

`workflow_instances.current_revision` increments on status changes (and some invalidations). Pass `expected_revision` on submit, pause, resume, cancel, and reopen to get `409 VERSION_CONFLICT` on stale clients. **The field is optional** — omitting it disables conflict detection.

---

## API reference

Base path: `/api/v1` unless noted.

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness |
| `GET` | `/ready` | Postgres + Redis checks |

### Definitions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/definitions/base-types` | List enabled base kinds |
| `POST` | `/definitions/nodes` | Publish node definition (new or new version) |
| `GET` | `/definitions/nodes` | List node summaries |
| `GET` | `/definitions/nodes/{slug}` | Get node (+ latest or `?version=`) |
| `GET` | `/definitions/nodes/{slug}/versions/{version}` | Get specific node version |
| `POST` | `/definitions/workflows` | Publish workflow |
| `GET` | `/definitions/workflows` | List workflow summaries |
| `GET` | `/definitions/workflows/{slug}` | Get workflow (+ latest or `?version=`) |
| `GET` | `/definitions/workflows/{slug}/versions/{version}` | Get specific workflow version |

### Instances

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/instances` | Start workflow instance |
| `GET` | `/instances?rfqId=…&incompleteOnly=false` | List instances by RFQ |
| `GET` | `/instances/rfq/{rfq_id}/incomplete` | Boolean incomplete check |
| `GET` | `/instances/export` | Excel export of **all** instances |
| `GET` | `/instances/{id}` | Full instance state + forms + summary |
| `GET` | `/instances/{id}/export` | Excel export of one instance |
| `POST` | `/instances/{id}/nodes/{workflow_node_id}/submit` | Submit task outputs |
| `POST` | `/instances/{id}/nodes/{workflow_node_id}/invalidate` | Reopen task + invalidate downstream |
| `POST` | `/instances/{id}/pause` | Pause (`expected_revision` optional body) |
| `POST` | `/instances/{id}/resume` | Resume + advance |
| `POST` | `/instances/{id}/cancel` | Cancel (optional `reason`) |
| `GET` | `/instances/{id}/events` | Event audit trail |
| `GET` | `/instances/{id}/node-executions` | Execution history rows |

### Backups

Also mounted at `/backups` (root alias).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/backups?limit=&offset=` | Paginated backup list |
| `POST` | `/backups` | Create backup |
| `POST` | `/backups/{backup_id}/restore` | Restore (requires `BACKUP_ALLOW_RESTORE`) |
| `DELETE` | `/backups/{backup_id}` | Delete backup file |

### Error responses

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

| Code | HTTP | When |
|------|------|------|
| `NOT_FOUND` | 404 | Missing resource |
| `VALIDATION_ERROR` | 422 | Definition / request validation |
| `FIELD_VALIDATION_FAILED` | 400 | Runtime form/table validation |
| `INVALID_TRANSITION` | 409 | Illegal status change |
| `UPSTREAM_NOT_READY` | 409 | Node not `PENDING` / upstream incomplete |
| `VERSION_CONFLICT` | 409 | Stale `expected_revision` |
| `SEQUENCE_CONFLICT` | 409 | Event sequence contention (after retries) |
| `INPUT_RESOLUTION_ERROR` | 409 | Missing upstream output or metadata key |
| `NODE_EXECUTION_ERROR` | 400 | Executor / graph errors |
| `DUPLICATE_SLUG` | 409 | Definition slug collision |

---

## Where to change what

| Task | Start here |
|------|------------|
| Add API endpoint | `app/modules/<feature>/router.py` |
| Add request/response DTO | `app/modules/<feature>/schemas.py` |
| Change orchestration logic | `app/application/executions/orchestrator.py` |
| Add node type (`baseKind`) | `app/domain/executors/` + `registry.py` + base_types seed/migration |
| Add validation rule | `app/domain/validation/` |
| Add event type / handler | `app/domain/events/` + `app/application/events/handlers/` |
| Change DB schema | SQLAlchemy model → `make migration msg='…'` → `make migrate` |
| Map new domain error to HTTP | `app/api/errors.py` |
| Backup deployment mode | `app/patterns/backups/strategies.py`, `factory.py` |

---

## Testing conventions

| Directory | Scope | Requires Postgres |
|-----------|-------|-------------------|
| `tests/unit/` | Domain, executors, validation, export | No |
| `tests/integration/` | Repositories, orchestrator, API, event store | Yes |
| `tests/fixtures/` | Sample node/workflow JSON | — |

- Mark integration tests: `@pytest.mark.integration`
- `make test` excludes integration; `make test-all` runs everything
- `api_client` fixture overrides DB session with rolled-back transaction per test

**Notable gaps in test coverage today:** concurrent parallel terminal submits, auth boundaries, bulk export at scale.

---

## Development commands

```bash
make install      # pip install dependencies
make lint         # ruff check
make format       # ruff format
make test         # unit tests only
make test-all     # all tests
make check        # lint + unit tests
make pre-commit   # git hooks
```

### PostgreSQL shortcuts

```bash
make up
make migrate
make migration msg='describe change'
make migrate-current
make migrate-history
make migrate-down
make db-psql
make db-logs
make db-wait
make db-reset
make db-backup
make db-restore file=backups/your.dump
```

---

## Extending the engine

### New node type

1. Implement executor in `app/domain/executors/` (subclass `BaseNodeExecutor` or implement `NodeExecutor`).
2. Register in `create_default_registry()`.
3. Add / enable row in `base_types` (migration if new kind).
4. Add definition schema validation if needed.
5. Unit tests for executor; integration test via orchestrator.

The orchestrator and submit API unchanged if the executor honors `ExecutionContext`.

### New event type

1. Add to `WorkflowEventType` enum.
2. Add payload dataclass in `domain/events/payloads.py`.
3. Extend `apply_workflow_projection_event` and/or add handler.
4. Emit from orchestrator at the correct lifecycle point.

---

## Further reading

- [DATABASE.md](DATABASE.md) — schema, migrations, write flows
- [ADR-001](adr/001-architecture-and-standards.md) — architecture decisions
- OpenAPI: http://localhost:8000/docs
- Sample workflow: `tests/fixtures/workflow_test.json`
