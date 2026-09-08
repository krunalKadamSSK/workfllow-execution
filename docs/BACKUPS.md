# Backup & Restore

PostgreSQL backup and restore for the Workflow Execution Engine. Three methods are supported:

| Method | Platform | Use case |
|--------|----------|----------|
| **Makefile** | Linux / macOS | Local dev, CI, scripts |
| **db.bat** | Windows (cmd.exe) | Local dev on Windows |
| **HTTP API** | Any | UI, automation, remote triggers |

All methods produce the same format: **PostgreSQL custom dump** (`pg_dump -Fc`) stored as `.dump` files. Dumps are **cross-platform** — a backup from Windows can be restored on Linux/macOS and vice versa.

---

## Table of contents

1. [What gets backed up](#what-gets-backed-up)
2. [Where backups are stored](#where-backups-are-stored)
3. [Prerequisites](#prerequisites)
4. [Environment configuration](#environment-configuration)
5. [Makefile (Linux / macOS)](#makefile-linux--macos)
6. [db.bat (Windows)](#dbbat-windows)
7. [HTTP API / UI](#http-api--ui)
8. [Cross-platform workflow](#cross-platform-workflow)
9. [How it works internally](#how-it-works-internally)
10. [Step-by-step scenarios](#step-by-step-scenarios)
11. [Troubleshooting](#troubleshooting)
12. [Security notes](#security-notes)
13. [Quick reference](#quick-reference)

---

## What gets backed up

| Setting | Default |
|---------|---------|
| Database | `workflow_engine` |
| Container | `workflow_engine_postgres` |
| User | `workflow` |
| Format | `pg_dump -Fc` (binary custom format, `.dump` extension) |
| Contents | Full schema + data (tables, indexes, constraints, etc.) |

Backups are **files on disk**, not stored inside PostgreSQL.

---

## Where backups are stored

| Source | Default directory | Resolved as |
|--------|-------------------|-------------|
| HTTP API / UI | `backups/` | `{app working directory}/backups/` |
| Makefile | `backups/` | Relative to project root when you run `make` |
| db.bat | `backups\` | Relative to where you run the script |

> **Note:** The folder is `backups/` (plural), not `backup/`.

**File naming:**

```
workflow_engine_YYYYMMDD_HHMMSS.dump
```

Example: `workflow_engine_28082026_145333.dump`

The HTTP API uses `BACKUP_STORAGE_DIR` from `.env`. If the path is relative, it is resolved from the **current working directory of the uvicorn process** (usually the project root).

---

## Prerequisites

### 1. Copy environment file

```bash
cp .env.example .env
```

### 2. Start infrastructure

```bash
make up
```

This starts:

- **Postgres** (`workflow_engine_postgres`) on port `5432`
- **Redis** (`workflow_engine_redis`) on port `6379`

### 3. Apply migrations (fresh database only)

If the database is empty (no tables), run:

```bash
make migrate
```

### 4. Verify Postgres is ready

```bash
make db-wait
```

Or check application readiness:

```bash
curl http://localhost:8000/ready
```

### 5. Start the API (for UI / HTTP backups)

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Environment configuration

Add these to `.env` (defaults shown):

```env
BACKUP_ENABLED=true
BACKUP_STORAGE_DIR=backups
BACKUP_DEPLOYMENT_MODE=docker
BACKUP_OS=auto
BACKUP_DOCKER_CONTAINER=workflow_engine_postgres
BACKUP_DOCKER_CLI=
BACKUP_POSTGRES_USER=workflow
BACKUP_TOOL_PATH=
BACKUP_ALLOW_RESTORE=true
BACKUP_RETENTION_COUNT=20
```

| Variable | Description |
|----------|-------------|
| `BACKUP_ENABLED` | `false` disables all HTTP backup operations (returns 403) |
| `BACKUP_STORAGE_DIR` | Directory for `.dump` files (relative or absolute path) |
| `BACKUP_DEPLOYMENT_MODE` | `docker` = pg_dump via container; `local` / `remote` = host `pg_dump` / `pg_restore` |
| `BACKUP_OS` | `auto`, `windows`, `linux`, `darwin` — affects tool resolution |
| `BACKUP_DOCKER_CONTAINER` | Postgres container name |
| `BACKUP_DOCKER_CLI` | Override docker binary path (e.g. `docker.exe`) |
| `BACKUP_POSTGRES_USER` | DB user for pg_dump / pg_restore |
| `BACKUP_TOOL_PATH` | Directory containing `pg_dump` / `pg_restore` if not on PATH |
| `BACKUP_ALLOW_RESTORE` | `false` blocks restore via API (returns 403) |
| `BACKUP_RETENTION_COUNT` | Max backups kept; oldest deleted after each new backup (`0` = no limit) |

**Recommended for production:**

```env
BACKUP_ALLOW_RESTORE=false
```

Enable restore only when explicitly needed.

---

## Makefile (Linux / macOS)

### Create backup

Auto-named file:

```bash
make db-backup
```

Creates `backups/workflow_engine_YYYYMMDD_HHMMSS.dump`.

Custom path:

```bash
make db-backup file=backups/my_backup.dump
```

**What it does:**

1. Waits for Postgres (`pg_isready`)
2. Runs `pg_dump -Fc` inside the container
3. Copies dump to host via `docker cp`
4. Removes temp file in container

### Restore backup

```bash
make db-restore file=backups/workflow_engine_28082026_145333.dump
```

With spaces in the filename — use quotes:

```bash
make db-restore file="backups/workflow_engine_21072026_144743 1 (1).dump"
```

> **Important:** No spaces around `=` in make commands.

```bash
# Wrong
make db-restore file = 'backups/my.dump'

# Correct
make db-restore file=backups/my.dump
```

**What restore does:**

1. Waits for Postgres
2. Copies dump into container
3. Runs `pg_restore --clean --if-exists`
4. Exit code `1` is treated as warnings only; fails only if exit code `> 1`

---

## db.bat (Windows)

Run from **cmd.exe** (not PowerShell) in the project root.

### Create backup

```bat
db.bat backup
db.bat backup backups\my_backup.dump
```

### Restore backup

```bat
db.bat restore backups\workflow_engine_28082026_145333.dump
db.bat restore "backups\workflow_engine_21072026_144743 1 (1).dump"
```

**Requirements on Windows:**

- Docker Desktop running
- `workflow_engine_postgres` container up
- `docker` on PATH

---

## HTTP API / UI

Routes are mounted at both:

- `/api/v1/backups` (primary)
- `/backups` (alias)

### List backups (paginated)

```bash
curl "http://localhost:8000/api/v1/backups?limit=50&offset=0"
```

Response:

```json
{
  "items": [
    {
      "id": "workflow_engine_28082026_145333",
      "filename": "workflow_engine_28082026_145333.dump",
      "size_bytes": 123456,
      "created_at": "2026-08-28T14:53:33+00:00",
      "database": "workflow_engine",
      "engine": "postgresql"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### Create backup

```bash
curl -X POST http://localhost:8000/api/v1/backups
```

Response (201):

```json
{
  "message": "Backup created successfully",
  "backup": {
    "id": "workflow_engine_20260902_070500",
    "filename": "workflow_engine_20260902_070500.dump"
  }
}
```

After creation, retention runs automatically (keeps the latest `BACKUP_RETENTION_COUNT` files).

### Restore backup

Use the **backup id** (filename without `.dump`):

```bash
curl -X POST http://localhost:8000/api/v1/backups/workflow_engine_28082026_145333/restore
```

### Delete backup

```bash
curl -X DELETE http://localhost:8000/api/v1/backups/workflow_engine_28082026_145333
```

### Swagger UI

Open http://localhost:8000/docs and use the **Backups** section.

---

## Cross-platform workflow

### Windows → Linux restore

1. On Windows: `db.bat backup` → get `backups\workflow_engine_....dump`
2. Copy file to Linux project: `backups/workflow_engine_....dump`
3. On Linux: `make db-restore file=backups/workflow_engine_....dump`

### Linux → Windows restore

1. On Linux: `make db-backup`
2. Copy `.dump` to Windows `backups\` folder
3. On Windows: `db.bat restore backups\workflow_engine_....dump`

---

## How it works internally

```
Client (UI / curl / Makefile / db.bat)
        │
        ├─ HTTP API ──► BackupHttpController ──► BackupService
        │                                              │
        └─ Makefile/db.bat ──► docker exec pg_dump/pg_restore
                                                       │
                                              BackupRepository (file storage)
                                                       │
                                              BackupStrategyFactory
                                                       │
                                    ┌──────────────────┴──────────────────┐
                                    │                                     │
                            docker mode                           local / remote mode
                    DockerPostgresBackupStrategy              HostPostgresBackupStrategy
                                    │                                     │
                            CommandRunner (pg_dump stdout / docker cp restore)
                                    │
                            backups/*.dump on disk
```

**Docker mode (default):**

- Backup: `docker exec ... pg_dump -Fc` → streams to host file
- Restore: `docker cp` dump into container, then `pg_restore` from file path (`pg_restore` does not read custom-format archives from stdin)

**Local mode:**

- Uses `pg_dump` / `pg_restore` installed on the host, connecting via `DATABASE_URL`

Implementation: `app/patterns/backups/` (Strategy + Repository patterns).

---

## Step-by-step scenarios

### Restore a Windows backup on Linux

```bash
# 1. Start Postgres
make up
make db-wait

# 2. Place the dump file
mkdir -p backups
cp "/path/to/workflow_engine_28082026_145333.dump" backups/

# 3. Restore
make db-restore file=backups/workflow_engine_28082026_145333.dump

# 4. Verify tables exist
docker exec workflow_engine_postgres psql -U workflow -d workflow_engine -c "\dt"

# 5. Start API and test
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/api/v1/definitions/workflows
```

### Create backup via UI / API

```bash
# 1. Ensure .env has backups enabled
#    BACKUP_ENABLED=true
#    BACKUP_STORAGE_DIR=backups
#    BACKUP_DEPLOYMENT_MODE=docker

# 2. Start services
make up && make db-wait
uvicorn app.main:app --reload --port 8000

# 3. Create backup
curl -X POST http://localhost:8000/api/v1/backups

# 4. Confirm file on disk
ls -la backups/

# 5. List via API
curl http://localhost:8000/api/v1/backups
```

---

## Troubleshooting

### `relation "workflow_definitions" does not exist`

**Cause:** Database is empty — no schema, or restore did not run.

**Fix:**

```bash
make db-restore file=backups/your_file.dump   # restore data
# or
make migrate                                   # fresh schema only
```

---

### `Backup file not found: backup/...`

**Cause:** Wrong folder (`backup/` vs `backups/`) or file not copied to the machine.

**Fix:**

```bash
ls -la backups/
make db-restore file=backups/actual_filename.dump
```

---

### `make: *** empty variable name. Stop.`

**Cause:** Spaces around `=` in the make command.

**Fix:**

```bash
make db-restore file=backups/my.dump
```

---

### `failed to bind host port 6379: address already in use`

**Cause:** Another Redis process is using port 6379. `make up` or `make db-reset` may fail partway.

**Fix:**

```bash
sudo lsof -i :6379
# Or change port in .env:
# REDIS_PORT=6380
```

If `db-reset` failed after wiping volumes, Postgres may be empty:

```bash
make migrate
# or restore your dump
```

---

### `pg_dump: connection to server failed` / container not found

**Cause:** Postgres container is not running.

**Fix:**

```bash
make up
docker ps --filter name=workflow_engine_postgres
make db-wait
```

---

### HTTP API returns `403 Backup operations are disabled`

**Cause:** `BACKUP_ENABLED=false` in `.env`.

**Fix:** Set `BACKUP_ENABLED=true` and restart uvicorn.

---

### HTTP API returns `403 Restore is disabled`

**Cause:** `BACKUP_ALLOW_RESTORE=false`.

**Fix:** Set `BACKUP_ALLOW_RESTORE=true` and restart uvicorn.

---

### HTTP API returns `404 Backup not found`

**Cause:** Wrong `backup_id`, or file not in `BACKUP_STORAGE_DIR`.

**Fix:**

- Use id **without** `.dump`: `workflow_engine_28082026_145333`
- Check file exists: `ls backups/`
- Ensure API working directory matches where `backups/` lives

---

### HTTP API returns `500 docker not found` or `pg_dump not found`

**Cause:** Docker or PostgreSQL client tools not on PATH.

**Fix for docker mode:**

```env
BACKUP_DEPLOYMENT_MODE=docker
BACKUP_DOCKER_CLI=/usr/bin/docker
```

**Fix for local mode:**

```env
BACKUP_DEPLOYMENT_MODE=local
BACKUP_TOOL_PATH=/usr/lib/postgresql/16/bin
```

---

### Restore shows warnings but completes

**Normal.** `pg_restore` often exits with code `1` for non-fatal warnings (e.g. "role does not exist"). Both Makefile and API treat exit code `1` as success.

---

### UI backup works but CLI restore cannot find file

**Cause:** Different working directories or `BACKUP_STORAGE_DIR` override.

**Fix:** Use the full path:

```bash
make db-restore file=/home/ssk/workfllow-execution/backups/workflow_engine_28082026_145333.dump
```

---

### `make db-reset` left database empty

**Cause:** `db-reset` runs `down -v` (wipes data), then `up`, then `migrate`. If `up` fails (e.g. Redis port conflict), migrate never runs.

**Fix:**

```bash
make migrate
# or
make db-restore file=backups/your_latest.dump
```

---

## Security notes

- Backup/restore endpoints have **no built-in authentication** — treat as admin operations.
- In production, set `BACKUP_ALLOW_RESTORE=false` unless restore is explicitly required.
- Restrict network access to backup endpoints at the gateway or firewall.
- Backup files contain full database data — protect the `backups/` directory permissions.

---

## Quick reference

| Action | Command |
|--------|---------|
| Backup (Linux / macOS) | `make db-backup` |
| Restore (Linux / macOS) | `make db-restore file=backups/file.dump` |
| Backup (Windows) | `db.bat backup` |
| Restore (Windows) | `db.bat restore backups\file.dump` |
| List (API) | `GET /api/v1/backups` |
| Create (API) | `POST /api/v1/backups` |
| Restore (API) | `POST /api/v1/backups/{id}/restore` |
| Delete (API) | `DELETE /api/v1/backups/{id}` |
| Storage dir | `backups/` (configurable via `BACKUP_STORAGE_DIR`) |
| Dump format | `pg_dump -Fc` (`.dump`) |
