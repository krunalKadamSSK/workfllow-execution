# AccessCore integration (Phases 0–6)

End-to-end auth for CostEstimationEngine-Frontend, CostEstimationEngine-Backend,
and this Workflow Engine.

## Components

| Service | Port (local) | Role |
|---------|--------------|------|
| AccessCore | 8081 | Login cookie, SSO exchange, introspect, authorize |
| CostEstimationEngine-Frontend | 5173 | Browser SSO; Bearer on API calls |
| CostEstimationEngine-Backend | 8000 | Masters/files; AccessCore-only middleware |
| Workflow Engine (this repo) | 8080 | Definitions/instances/backups; `require_permission` |

## Bootstrap AccessCore

```bash
cd /home/ssk/AccessCore
python -m app.application.rbac_seed
python -m app.application.integration_seed
```

Save printed:

- Frontend `client_id` → `VITE_ACCESSCORE_CLIENT_ID`
- API keys `cost-backend` / `workflow-execution` → each backend `ACCESSCORE_API_KEY`
  (or shared `AUTHORIZE_API_KEY=local-authorize-key`)

Demo users (password `password1`): `admin`, `estimator`, `cad_expert`.

## Frontend `.env`

```bash
VITE_ACCESSCORE_BASE_URL=http://localhost:8081
VITE_ACCESSCORE_CLIENT_ID=<from integration_seed>
VITE_ACCESSCORE_REDIRECT_URI=http://localhost:5173/auth/callback
VITE_CONFIG_API_BASE_URL=http://localhost:8000
VITE_EXECUTION_API_BASE_URL=http://localhost:8080
```

## Backend `.env`

```bash
# CostEstimationEngine-Backend
ACCESSCORE_ENABLED=true
ACCESSCORE_URL=http://localhost:8081
ACCESSCORE_API_KEY=<cost-backend key or local-authorize-key>

# workfllow-execution
ACCESSCORE_ENABLED=true
ACCESSCORE_URL=http://localhost:8081
ACCESSCORE_API_KEY=<workflow-execution key or local-authorize-key>
```

Automated pytest for this engine should keep `ACCESSCORE_ENABLED=false` (guards no-op).

## Permission map (Workflow Engine)

| Area | Permission |
|------|------------|
| Definitions workflows read/list | `workflow_definition.read` |
| Publish workflow | `workflow_definition.create` |
| Nodes read | `node_definition.read` |
| Publish node | `node_definition.create` |
| Instances read/export | `workflow_instance.read` |
| Start instance | `workflow_instance.create` |
| Submit/pause/cancel | `workflow_instance.update` |
| Backups | `backups.read` / `.create` / `.update` / `.delete` (admin) |

Estimator/cad_expert: CAD/CAM + estimate ops + workflow get/run.  
Admin: also node/workflow design + backups.

## E2E checklist

1. AccessCore healthy: `GET http://localhost:8081/health`
2. FE login with `admin` / `password1` → redirect SSO → callback stores Bearer token
3. Config API calls include `Authorization: Bearer …` and succeed for CAD/RFQ
4. Estimator can start/run workflow instance; cannot `POST /api/v1/definitions/nodes`
5. Without Bearer and `ACCESSCORE_ENABLED=true`, workflow APIs return 401
6. Logout clears FE session; subsequent API calls fail auth

## Curl smoke (authorize)

```bash
curl -s -X POST http://localhost:8081/v1/authorize \
  -H "X-AccessCore-Key: local-authorize-key" \
  -H "Content-Type: application/json" \
  -d '{"subject":"<user-id>","action":"create","resource":"node_definition","context":{}}'
```
