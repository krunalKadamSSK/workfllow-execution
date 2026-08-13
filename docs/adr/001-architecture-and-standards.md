# ADR-001: Architecture and Coding Standards

**Status:** Accepted (amended)
**Date:** 2026-06-18
**Last updated:** 2026-08-13
**Phase:** 1 — Runtime engine (definitions, executions, events, backups)

## Context

We are building a workflow execution engine with:

- Versioned workflow and node definitions from a React Flow frontend
- Event-sourced runtime state in PostgreSQL with synchronous projections
- Pluggable node executors (`userInput`, `table`)
- Upstream task outputs and instance metadata feeding downstream task inputs
- RFQ-linked workflow revisions, seed-from-prior-instance, reopen/invalidate, and Excel export
- Optional database backup/restore (Makefile + HTTP API)

The codebase must remain maintainable as node types and orchestration rules grow.

This ADR records **architectural decisions and standards**. For operational detail (API, schema, curl examples), see [Developer Guide](../DEVELOPER_GUIDE.md) and [Database](../DATABASE.md).

---

## Decision

Adopt a **layered, ports-and-adapters architecture** guided by **SOLID** and selected [design patterns](https://refactoring.guru/design-patterns).

### Package layout (current)

```
app/
  api/                  # Shared HTTP: deps, exception handlers, pagination schemas
    controllers/        # Thin controllers (e.g. backups)
    v1/                 # Health routes
  modules/              # Feature routers + request/response DTOs
    definitions/        # Publish & list definitions
    executions/         # Instance lifecycle, export
    backups/            # Backup HTTP routes
  application/          # Use cases, orchestrator, facades, event store
    definitions/        # DefinitionIngestService
    executions/         # WorkflowOrchestrator, scheduler, export, seed memento
    events/             # EventStore, handlers, ProjectionRebuilder
    backups/            # BackupService facade
  domain/               # Pure logic: graph, executors, validation, state machines, ports
  infrastructure/       # SQLAlchemy models, repositories, projection readers, Redis client
  patterns/             # Cross-cutting pattern implementations (backups subsystem)
  core/                 # Config, logging, CORS, middleware, DB session factory
```

**Dependency rule:** `domain` imports nothing from outer layers. `application` depends on `domain` ports and orchestrates repositories. `infrastructure` and `modules` call inward. `patterns/` may depend on `core` and external libraries but not on `modules`.

### SOLID mapping

| Principle | Rule in this project |
|-----------|----------------------|
| **S** — Single responsibility | Validators, executors, repositories, handlers, and routers change for different reasons |
| **O** — Open/closed | New node types via new `NodeExecutor` + `NodeExecutorRegistry.register()` |
| **L** — Liskov substitution | All executors honor `NodeExecutor` / `BaseNodeExecutor` contract |
| **I** — Interface segregation | Small protocols: `NodeExecutor`, `InputResolver`, `NodeProjectionReader`, `EventHandler` |
| **D** — Dependency inversion | Orchestrator depends on repository and registry abstractions wired in `ExecutionService.from_session()` |

### Design patterns (implemented)

| Pattern | Where | Purpose |
|---------|-------|---------|
| **Strategy** | `UserInputExecutor`, `TableExecutor`, backup strategies (`DockerPostgresBackupStrategy`, `HostPostgresBackupStrategy`) | Swap behavior by kind or deployment mode |
| **State** | `WorkflowStateMachine`, `NodeStateMachine` | Legal status transitions |
| **Command** | Append-only `WorkflowEvent` rows | Event sourcing audit trail |
| **Template Method** | `BaseNodeExecutor.run()` | prepare → validate → complete |
| **Factory Method** | `NodeExecutorRegistry`, `BackupStrategyFactory` | Resolve implementation by key |
| **Mediator** | `WorkflowOrchestrator` | Coordinate lifecycle without fat controllers |
| **Observer** | `EventHandlerRegistry` + projection/snapshot handlers | React to appended events |
| **Repository** | `*Repository` under `infrastructure/db/repositories` | Persistence access |
| **Facade** | `ExecutionService`, `BackupService` | Stable entry points for modules |
| **Memento** | `WorkflowSnapshot` (graph pin), `SeedDefaultsMemento` (static defaults from prior revision) | Capture/restorable state |
| **Builder** | `WorkflowInstanceBuilder` | Construct instance + pinned node rows |
| **Unit of Work** | `UnitOfWork` (optional context manager) | Multi-repo transaction boundary |
| **Template Method (ops)** | `BackupStrategy.create_backup` / `restore_backup` | Shared backup orchestration hooks |

Validation pipelines (`validate_workflow_definition`, `GraphInputBinder`) follow a **chain-of-responsibility** style but are implemented as explicit function composition, not a framework.

### Runtime model

| Aspect | Decision |
|--------|----------|
| **Execution** | Synchronous in the HTTP request thread — no job queue |
| **Transactions** | Mutating routes call `session.commit()` explicitly after use cases; `get_db()` rolls back on exception |
| **Event dispatch** | Handlers run inline in `EventStore.append()` before commit — projections and snapshots stay consistent with events in one transaction |
| **Definition pinning** | Instance pins workflow + node definition version ids at start; graph snapshot stored on `WORKFLOW_STARTED` |
| **Concurrency** | Optimistic revision on workflow status (`expected_revision`, optional); event sequence uniqueness with retry; **no row locks today** — see Known gaps |
| **Idempotency** | Submit is not idempotent; retry after success returns `409 UPSTREAM_NOT_READY` |

### Node executors

| `baseKind` | Implementation | Notes |
|------------|----------------|-------|
| `userInput` | `UserInputExecutor` | Synapse form fields; locked upstream validation |
| `table` | `TableExecutor` | Header + rows; server-side aggregations; `FormFieldValidator` |

Registration: `create_default_registry()` in `app/domain/executors/registry.py`. Catalog rows in `base_types` (migrations `002`–`004`).

### Persistence

- **ORM:** SQLAlchemy 2.0 (sync) with **psycopg3** (`postgresql+psycopg://`)
- **Migrations:** Alembic (`4a780231d1ef` → `006_search_list_indexes`)
- **Pool defaults:** `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`
- **Redis:** client exists; used **only** for `GET /ready` — not for caching, locks, or queues

Database URLs may be supplied as `postgresql://`, `postgres://`, or `postgresql+asyncpg://`; normalized to `postgresql+psycopg://` in settings.

**Source of truth:** `workflow_events`. **Read models:** `workflow_projections`, `workflow_node_projections`. **Recovery:** `ProjectionRebuilder.rebuild()` replays events (tests / `UnitOfWork` — no public HTTP endpoint yet).

### Security boundary

**Decision (deferred):** Application-layer authentication and authorization are **not implemented**. All routes are open to callers that reach the process.

**Expectation for production:** Enforce authn/authz at an API gateway, service mesh, or reverse proxy. Treat these as admin-only until protected:

- `POST /api/v1/backups/{id}/restore`
- `GET /api/v1/instances/export`
- `POST /api/v1/definitions/*`

Audit fields (`created_by`, `executed_by`) are client-supplied strings — not trustworthy without authenticated identity.

### Error taxonomy

All API errors use a consistent JSON shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable summary",
    "details": [],
    "request_id": "uuid-from-X-Request-ID"
  }
}
```

Handlers in `app/api/errors.py`. Domain exceptions in `app/domain/exceptions.py`.

| Code | HTTP | When |
|------|------|------|
| `NOT_FOUND` | 404 | Missing resource |
| `VALIDATION_ERROR` | 422 | Invalid definition or domain validation |
| `FIELD_VALIDATION_FAILED` | 400 | Runtime form/table validation (`details` = field errors) |
| `NODE_EXECUTION_ERROR` | 400 | Executor/graph/runtime execution errors |
| `INVALID_TRANSITION` | 409 | Illegal workflow or node status change |
| `UPSTREAM_NOT_READY` | 409 | Node not submittable (not `PENDING`) |
| `INPUT_RESOLUTION_ERROR` | 409 | Missing upstream output or metadata key |
| `VERSION_CONFLICT` | 409 | Stale `expected_revision` |
| `SEQUENCE_CONFLICT` | 409 | Event sequence contention after retries |
| `DUPLICATE_SLUG` | 409 | Definition slug collision |
| `WORKFLOW_ENGINE_ERROR` | 500 | Unhandled domain/base errors |

**Not implemented:** `DUPLICATE_SUBMIT` / submit idempotency codes. SQLAlchemy `IntegrityError` from race conditions may surface as unhandled 500.

Backup errors use `BackupServiceError` → HTTP via controller (`403`/`404`/`500`/`504`).

### Observability

| Capability | Status |
|------------|--------|
| Request correlation | `X-Request-ID` via `RequestContextMiddleware` |
| Structured logging config | `app.core.logging` — JSON when `LOG_JSON=true` |
| Application log statements | **Minimal today** — rely on uvicorn access logs unless extended |
| Liveness | `GET /health` |
| Readiness | `GET /ready` (PostgreSQL + Redis) |
| Metrics / tracing | Not implemented |

**Standard:** New mutation paths should log structured fields (`request_id`, `workflow_instance_id`, `workflow_node_id`, outcome). Do not log secrets or full PII payloads.

### Testing standards

| Layer | Location | Requires Postgres |
|-------|----------|-------------------|
| Unit | `tests/unit/` | No |
| Integration | `tests/integration/` (`@pytest.mark.integration`) | Yes — auto-skip if DB unreachable |
| API | `tests/integration/test_*_api.py` via `api_client` fixture | Yes |

```bash
make test       # pytest -m "not integration"  (CI default)
make test-all   # includes integration
make check      # ruff + unit tests
```

**CI (`.github/workflows/ci.yml`):** ruff lint, ruff format check, unit tests only — **integration tests not run in CI today**.

Integration tests use a rolled-back nested transaction per test (`tests/conftest.py`).

### Code quality

- **Ruff** lint + format (`pyproject.toml`, Python 3.11)
- **Pre-commit** hooks (`make pre-commit`)
- **pytest** with `integration` marker

---

## Known gaps and follow-up work

Documented here so ADR stays honest about current boundaries. Not blockers for local development; blockers for unsupervised production deploy.

| Gap | Risk | Intended direction |
|-----|------|-------------------|
| No authn/authz | Open admin surface | Gateway auth or app middleware + roles |
| Parallel terminal submit race | Workflow stuck `RUNNING` | Lock workflow row or atomic completion update |
| Workflow projection RMW | Lost updates under concurrent events | `FOR UPDATE` or sequence CAS on projection |
| No submit idempotency | Ambiguous retry after timeout | `Idempotency-Key` or payload-hash dedup |
| Optional `expected_revision` | Lost updates | Require on mutations or enforce in clients |
| No payload size / row caps | Memory/DoS | Server-side limits on table submit and metadata |
| Redis in readiness but unused | False-negative deploy readiness | Remove from `/ready` or use Redis for locks/cache |
| `ProjectionRebuilder` not exposed | Hard operational recovery | Admin endpoint + metadata resync |
| `NODE_FAILED` not emitted | Incomplete failure model | Emit when async/side-effect executors added |
| Live restore during traffic | Schema corruption | Maintenance mode + connection drain before restore |

---

## Consequences

**Positive**

- Clear boundaries: definitions, executions, events, backups evolve independently
- New node types register without changing orchestrator control flow
- Domain logic testable without FastAPI or PostgreSQL
- Event log enables audit and projection rebuild
- Pinned versions + snapshots prevent silent graph drift mid-run

**Negative**

- Package count and indirection higher than a monolith script
- Sync execution blocks HTTP workers; large table validation ties up pool connections
- Explicit `session.commit()` in routers — easy to forget on new endpoints
- Read routes hold implicit DB transactions until response completes
- Security and hard concurrency guarantees deferred to infrastructure or future work

---

## References

- [Developer Guide](../DEVELOPER_GUIDE.md) — API, flows, commands
- [Database](../DATABASE.md) — schema, migrations, write paths
- [Refactoring.Guru — Design Patterns](https://refactoring.guru/design-patterns)
- Sample fixtures: `tests/fixtures/`
