#!/usr/bin/env bash
# Run Alembic against the platform-infra workflow Postgres (cep stack).
#
# Usage:
#   ./scripts/migrate-platform.sh              # upgrade head (default)
#   ./scripts/migrate-platform.sh upgrade
#   ./scripts/migrate-platform.sh current
#   ./scripts/migrate-platform.sh history
#   ./scripts/migrate-platform.sh downgrade
#
# Env overrides:
#   PLATFORM_INFRA   path to cost-estimation-platform-infra (default: ../cost-estimation-platform-infra)
#   PLATFORM_NETWORK docker network name (default: cep_cep-net)
#   PLATFORM_IMAGE   image tag (default: cep-workflow-api:local)
#   SKIP_BUILD=1     skip docker build (use existing image)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLATFORM_INFRA="${PLATFORM_INFRA:-$ROOT/../cost-estimation-platform-infra}"
PLATFORM_ENV="${PLATFORM_ENV:-$PLATFORM_INFRA/.env}"
PLATFORM_NETWORK="${PLATFORM_NETWORK:-cep_cep-net}"
PLATFORM_IMAGE="${PLATFORM_IMAGE:-cep-workflow-api:local}"
ACTION="${1:-upgrade}"

if [[ ! -f "$PLATFORM_ENV" ]]; then
  echo "ERROR: platform .env not found: $PLATFORM_ENV"
  echo "Set PLATFORM_INFRA=/path/to/cost-estimation-platform-infra"
  exit 1
fi

if ! docker network inspect "$PLATFORM_NETWORK" >/dev/null 2>&1; then
  echo "ERROR: docker network '$PLATFORM_NETWORK' not found."
  echo "Start the platform stack first:"
  echo "  cd $PLATFORM_INFRA && ./scripts/compose.sh up -d"
  exit 1
fi

# shellcheck disable=SC1090
set -a
# Prefer DOCKER_HOST like infra scripts
if [[ -z "${DOCKER_HOST:-}" && -S /var/run/docker.sock ]]; then
  export DOCKER_HOST=unix:///var/run/docker.sock
fi
source "$PLATFORM_ENV"
set +a

: "${POSTGRES_WORKFLOW_PASSWORD:?POSTGRES_WORKFLOW_PASSWORD missing in $PLATFORM_ENV}"
USER="${POSTGRES_WORKFLOW_USER:-workflow}"
DB="${POSTGRES_WORKFLOW_DB:-workflow_engine}"
DATABASE_URL="postgresql+psycopg://${USER}:${POSTGRES_WORKFLOW_PASSWORD}@postgres-workflow:5432/${DB}"

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  echo "==> Building $PLATFORM_IMAGE from $ROOT"
  docker build --network=host -t "$PLATFORM_IMAGE" "$ROOT"
else
  echo "==> SKIP_BUILD=1 — using existing $PLATFORM_IMAGE"
fi

case "$ACTION" in
  upgrade|head)
    CMD=(alembic upgrade head)
    ;;
  current)
    CMD=(alembic current)
    ;;
  history)
    CMD=(alembic history -v)
    ;;
  downgrade|down)
    CMD=(alembic downgrade -1)
    ;;
  *)
    echo "Usage: $0 [upgrade|current|history|downgrade]"
    exit 1
    ;;
esac

echo "==> Running: ${CMD[*]} on platform DB ($DB)"
docker run --rm \
  --network "$PLATFORM_NETWORK" \
  -e DATABASE_URL="$DATABASE_URL" \
  "$PLATFORM_IMAGE" \
  "${CMD[@]}"
