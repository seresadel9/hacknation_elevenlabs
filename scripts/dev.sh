#!/usr/bin/env bash
# Start the Umbra backend (FastAPI, :8000) and frontend (Next.js, :3000) together. Ctrl+C stops both.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT/backend"
if command -v uv >/dev/null 2>&1; then
  uv sync --quiet
  uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
else
  python3 -m venv .venv && . .venv/bin/activate
  pip install --quiet fastapi "uvicorn[standard]" pydantic pydantic-settings httpx python-multipart
  uvicorn app.main:app --host 0.0.0.0 --port 8000 &
fi
BACK=$!
trap 'kill $BACK 2>/dev/null || true' EXIT

cd "$ROOT/frontend"
[ -d node_modules ] || npm install
npm run dev -- --hostname 0.0.0.0 --port 3000
