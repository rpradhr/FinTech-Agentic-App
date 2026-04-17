#!/usr/bin/env bash
# One-shot dev environment setup.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> FinTech Agentic App — Local Setup"

# Copy .env if missing
if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "==> .env created from .env.example — please fill in your values"
fi

# Backend
echo "==> Setting up Python backend..."
cd "$ROOT/backend"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e ".[dev]"

# Frontend
echo "==> Setting up Node frontend..."
cd "$ROOT/frontend"
npm install

# Make scripts executable
chmod +x "$ROOT/scripts/"*.sh

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit .env with your Couchbase and Capella credentials"
echo "  2. Run: ./scripts/dev.sh"
echo "  3. Open: http://localhost:5173"
