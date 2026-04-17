#!/usr/bin/env bash
# Lint and format-check both backend and frontend.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Backend lint (ruff)"
(cd "$ROOT/backend" && .venv/bin/ruff check app tests && .venv/bin/ruff format --check app tests)

echo "==> Backend type check (mypy)"
(cd "$ROOT/backend" && .venv/bin/mypy app)

echo "==> Frontend lint (eslint)"
(cd "$ROOT/frontend" && npm run lint)

echo "==> Frontend type check (tsc)"
(cd "$ROOT/frontend" && npm run typecheck)

echo "All lint checks passed."
