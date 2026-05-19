#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${API_HOST:=127.0.0.1}"
: "${API_PORT:=8000}"

uvicorn backend.app.main:app --reload --host "${API_HOST}" --port "${API_PORT}" &
API_PID=$!

npm run dev &
WEB_PID=$!

trap 'kill ${API_PID} ${WEB_PID} 2>/dev/null || true' EXIT
wait
