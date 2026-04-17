#!/usr/bin/env bash
# Start both backend and frontend dev servers concurrently.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Starting FinTech Agentic App in development mode"

# Backend
(
  cd "$ROOT/backend"
  if [ ! -d ".venv" ]; then
    echo "==> Creating Python venv..."
    python3 -m venv .venv
    .venv/bin/pip install -e ".[dev]"
  fi
  echo "==> Starting FastAPI backend on :8000"
  .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!

# Frontend
(
  cd "$ROOT/frontend"
  if [ ! -d "node_modules" ]; then
    echo "==> Installing frontend deps..."
    npm install
  fi
  echo "==> Starting Vite frontend on :5173"
  npm run dev
) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
