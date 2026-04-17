#!/usr/bin/env bash
# Run all backend and frontend tests.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0

echo "==> Running backend tests"
(
  cd "$ROOT/backend"
  .venv/bin/pytest tests/ -v --cov=app --cov-report=term-missing
) || FAILED=1

echo ""
echo "==> Running frontend tests"
(
  cd "$ROOT/frontend"
  npm test
) || FAILED=1

if [ $FAILED -ne 0 ]; then
  echo ""
  echo "ERROR: One or more test suites failed." >&2
  exit 1
fi

echo ""
echo "All tests passed."
