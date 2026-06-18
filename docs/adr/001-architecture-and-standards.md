# ADR-001: Architecture and Coding Standards

**Status:** Accepted  
**Date:** 2026-06-18  
**Phase:** 0 — Foundation

## Context

We are building a production workflow execution engine with:

- Versioned workflow and node definitions from a React Flow frontend
- Event-sourced runtime state (PostgreSQL)
- Pluggable node executors starting with `userInput`, expanding later
- Upstream task outputs feeding downstream task inputs

The codebase must remain maintainable as node types and orchestration rules grow.

## Decision

Adopt a **layered, ports-and-adapters architecture** guided by **SOLID** and selected [design patterns](https://refactoring.guru/design-patterns).

### Package layout

```
app/
  api/              # HTTP routers, request/response DTOs, exception handlers
  application/      # Use cases, orchestrator, facades
  domain/           # Entities, value objects, ports (protocols), domain errors
  infrastructure/   # SQLAlchemy, Redis, external HTTP adapters
  core/             # Cross-cutting: config, logging, middleware
  modules/          # Feature-grouped API modules (definitions, executions)
```

**Dependency rule:** `domain` imports nothing from outer layers. `application` depends on `domain` ports. `infrastructure` and `api` implement or call inward.

### SOLID mapping

| Principle | Rule in this project |
|-----------|----------------------|
| **S** — Single responsibility | One reason to change per class/module (e.g. validators ≠ executors ≠ repositories) |
| **O** — Open/closed | New node types via new `NodeExecutor` implementations + factory registration |
| **L** — Liskov substitution | All executors honor the same execution contract |
| **I** — Interface segregation | Small protocols: `NodeExecutor`, `EventStore`, `InputResolver`, `ProjectionWriter` |
| **D** — Dependency inversion | Application code depends on abstractions; SQLAlchemy/Redis are adapters |

### Design patterns (planned usage)

| Pattern | Usage |
|---------|--------|
| **Strategy** | Node executors per `baseKind` |
| **State** | Workflow and node status transitions |
| **Command** | Append-only `WorkflowEvent` records |
| **Template Method** | Shared executor lifecycle: prepare → validate → complete |
| **Factory Method** | `NodeExecutorFactory` resolves executor by kind |
| **Chain of Responsibility** | Validation and input-resolution pipelines |
| **Mediator** | `WorkflowOrchestrator` coordinates nodes |
| **Observer** | Event handlers update projections |
| **Repository** | Persistence behind domain ports |
| **Facade** | `ExecutionService` as API entry point |
| **Memento** | `WorkflowSnapshot` for recovery |

### Persistence

- **ORM:** SQLAlchemy 2.0 (sync) with **psycopg3** driver
- **Migrations:** Alembic
- **Redis:** readiness checks only (`GET /ready`); execution is synchronous in the API process

Database URLs may be supplied as `postgresql://` or `postgresql+asyncpg://`; the app normalizes them to `postgresql+psycopg://` at startup.

### Error taxonomy

All API errors use a consistent JSON shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable summary",
    "details": [],
    "request_id": "uuid"
  }
}
```

| Code | HTTP | When |
|------|------|------|
| `VALIDATION_ERROR` | 422 | Invalid definition or request shape |
| `NOT_FOUND` | 404 | Missing resource |
| `INVALID_TRANSITION` | 409 | Illegal status change |
| `UPSTREAM_NOT_READY` | 409 | Node submitted before dependencies complete |
| `FIELD_VALIDATION_FAILED` | 400 | Runtime form validation failure |
| `VERSION_CONFLICT` | 409 | Optimistic concurrency conflict |
| `DUPLICATE_SUBMIT` | 409 | Idempotency violation |
| `INTERNAL_ERROR` | 500 | Unexpected failure (no stack trace in production) |

### Observability (Phase 0)

- Structured logging via `app.core.logging` (JSON optional via `LOG_JSON=true`)
- Request correlation via `X-Request-ID` header (`app.core.middleware`)
- Liveness: `GET /health`
- Readiness: `GET /ready` (PostgreSQL + Redis)

### Testing standards

- **Unit tests:** domain logic, validators, state machines — no I/O
- **Integration tests:** repositories, orchestrator — require Postgres/Redis (docker-compose)
- **API tests:** httpx `TestClient`; mock readiness for CI without infrastructure

### Code quality

- **Ruff** for lint and format (`pyproject.toml`)
- **Pre-commit** hooks for local checks
- **CI** (GitHub Actions): ruff + pytest on push/PR

## Consequences

**Positive**

- Clear boundaries for phased delivery (definitions → executors → events → API)
- New node types added without modifying orchestrator core
- Testable domain logic isolated from FastAPI and SQLAlchemy

**Negative**

- More packages and indirection early in the project
- Sync execution in the request thread — long-running node work blocks the HTTP response

## References

- [Refactoring.Guru — Design Patterns](https://refactoring.guru/design-patterns)
- Workflow schema and React Flow definition JSON (project design docs)
