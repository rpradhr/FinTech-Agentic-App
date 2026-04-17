#!/usr/bin/env bash
# Seed sample data into the configured datastore (Couchbase or in-memory dev mode).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Seeding sample banking data..."
cd "$ROOT/backend"
.venv/bin/python -m app.scripts.seed_data "$@"
echo "==> Seed complete."
