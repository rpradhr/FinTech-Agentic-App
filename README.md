# FinTech Agentic Banking Platform

A production-ready, multi-agent banking operations platform built on LangGraph-style orchestration, FastAPI, and React. Specialist AI agents handle fraud triage, customer sentiment, loan underwriting, branch performance monitoring, and financial advisory — each with mandatory human-in-the-loop approval gates and a full audit trail.

---

## Key Capabilities

- **Fraud Detection Agent** — Scores inbound transactions in real time, generates risk explanations, and raises alerts that a fraud analyst must approve before any account action is taken.
- **Sentiment Analysis Agent** — Classifies customer interactions (call transcripts, chat logs, survey responses) to surface at-risk relationships and suppress cross-sell when appropriate.
- **Loan Review Agent** — Automates the initial underwriting pass: document completeness checks, DTI/LTV calculations, credit signal synthesis, and a structured recommendation that requires underwriter sign-off.
- **Branch Monitoring Agent** — Ingests branch KPI timeseries (wait times, staffing, complaint counts, new accounts) and produces ranked operational recommendations for branch managers.
- **Financial Advisory Agent** — Assembles a holistic customer profile and generates next-best-action advice drafts that a licensed advisor must review and approve before delivery.
- **Human-in-the-Loop (HITL) Gates** — Every consequential agent output requires explicit human approval via API. Agents never act autonomously on customer data.
- **Immutable Audit Trail** — All agent LLM calls, tool invocations, human decisions, and state transitions are persisted as structured audit events with actor, timestamp, and input/output summaries.

---

## Repository Structure

```
FinTech-Agentic-App/
├── backend/
│   ├── app/
│   │   ├── domain/            # Pure domain models (no infrastructure deps)
│   │   │   └── models/        # CustomerProfile, Transaction, FraudAlert, LoanApplication, …
│   │   ├── application/       # Use-case layer: agents + orchestrator
│   │   │   ├── agents/        # fraud.py, loan.py, sentiment.py, advisory.py, branch.py, base.py
│   │   │   └── orchestrator.py
│   │   ├── infrastructure/    # Adapters (swappable implementations)
│   │   │   ├── ai/            # capella.py (Capella Model Service), stub.py, interfaces.py
│   │   │   └── persistence/   # couchbase/, memory/ (in-memory for dev/test), interfaces.py
│   │   ├── api/               # FastAPI layer
│   │   │   ├── routers/       # fraud.py, loans.py, advisory.py, branches.py, auth_router.py, …
│   │   │   ├── auth.py        # JWT validation, RBAC, dev-token helper
│   │   │   └── schemas.py     # Pydantic request/response models
│   │   ├── core/              # Cross-cutting concerns
│   │   │   ├── config.py      # pydantic-settings, env-var schema
│   │   │   ├── container.py   # Dependency injection wiring
│   │   │   ├── ids.py         # ULID generators
│   │   │   └── logging.py     # Structured logging setup
│   │   ├── scripts/
│   │   │   └── seed_data.py   # Sample data seeder
│   │   └── main.py            # FastAPI app factory + lifespan
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── pages/             # FraudWorkbench, LoanWorkbench, AdvisorWorkspace, BranchMonitor, …
│       ├── components/        # Layout, RiskBadge, StatusBadge
│       ├── services/          # api.ts, auth.ts — typed HTTP client
│       ├── store/             # auth.ts — lightweight state
│       └── types/             # Shared TypeScript interfaces
├── scripts/
│   ├── setup.sh               # One-shot environment bootstrap
│   ├── dev.sh                 # Start backend + frontend concurrently
│   ├── seed.sh                # Populate datastore with sample data
│   ├── test.sh                # Run all tests (backend + frontend)
│   └── lint.sh                # Ruff + mypy + ESLint + tsc
└── docs/
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend runtime | Python 3.11 |
| API framework | FastAPI 0.111+ with Uvicorn |
| Agent orchestration | LangGraph + LangChain Core |
| Data validation | Pydantic v2 / pydantic-settings |
| Authentication | python-jose (JWT / HS256), OIDC-ready |
| Primary datastore | Couchbase Capella (managed cloud) |
| Dev/test datastore | In-memory adapter (no external deps) |
| AI / LLM | Capella Model Service (OpenAI-compatible endpoint) |
| LLM fallback | OpenAI API or Anthropic API (dev/test) |
| Frontend framework | React 18 + TypeScript |
| Frontend build | Vite |
| Styling | Tailwind CSS |
| Observability | OpenTelemetry (OTLP export) + structlog |

---

## Quick Start

```bash
# 1. Clone
git clone <repository-url> FinTech-Agentic-App
cd FinTech-Agentic-App

# 2. Copy and edit environment config
cp .env.example .env
# Open .env in your editor and fill in credentials (see table below)

# 3. Bootstrap Python venv and install Node packages
./scripts/setup.sh

# 4. Seed sample data (customers, transactions, loan applications, branch KPIs)
./scripts/seed.sh

# 5. Start backend (port 8000) and frontend (port 5173) concurrently
./scripts/dev.sh
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Environment Variables

Copy `.env.example` to `.env` and set values appropriate for your environment.

| Variable | Required | Description |
|---|---|---|
| `APP_ENV` | No | `development` (default), `test`, `staging`, or `production` |
| `APP_SECRET_KEY` | Yes (prod) | Secret used to sign dev JWTs. Change in production. |
| `COUCHBASE_CONNECTION_STRING` | No* | Capella connection string, e.g. `couchbases://cb.xxx.cloud.couchbase.com`. Leave blank to use the in-memory adapter. |
| `COUCHBASE_USERNAME` | No* | Couchbase database username |
| `COUCHBASE_PASSWORD` | No* | Couchbase database password |
| `CAPELLA_AI_ENDPOINT` | No* | Capella Model Service base URL (OpenAI-compatible). Leave blank to use the stub LLM. |
| `CAPELLA_AI_API_KEY` | No* | API key for Capella Model Service |
| `OPENAI_API_KEY` | No | Fallback LLM key used when Capella is not configured |
| `ANTHROPIC_API_KEY` | No | Alternative fallback LLM key |

\* Not required for local development — the platform automatically falls back to in-memory persistence and a stub LLM when these are absent.

---

## Commands

```bash
# Development (hot-reload backend + frontend)
./scripts/dev.sh

# Run all tests
./scripts/test.sh

# Backend tests only
cd backend && .venv/bin/pytest tests/ -v

# Lint and type-check
./scripts/lint.sh

# Backend lint only (ruff)
cd backend && .venv/bin/ruff check app tests

# Backend type check (mypy)
cd backend && .venv/bin/mypy app

# Frontend lint (ESLint)
cd frontend && npm run lint

# Frontend type check
cd frontend && npm run typecheck

# Frontend production build
cd frontend && npm run build
```

---

## Troubleshooting

**No Couchbase account?**
Leave `COUCHBASE_CONNECTION_STRING` empty (or unset) and set `APP_ENV=development`. The platform automatically selects the in-memory persistence adapter. All workflows function identically; data is lost when the server restarts.

**No AI credentials?**
Leave `CAPELLA_AI_ENDPOINT` and `OPENAI_API_KEY` empty. A stub LLM adapter returns deterministic placeholder responses so all API endpoints remain fully exercisable. Set real credentials to enable genuine LLM-powered analysis.

**Port conflicts**
The backend defaults to `:8000` and the frontend to `:5173`. To change them, edit `scripts/dev.sh` (pass `--port NNNN` to Uvicorn) and `frontend/vite.config.ts` (set `server.port`). Update `FRONTEND_ORIGIN` and `CORS_ALLOWED_ORIGINS` in `.env` accordingly.

**`ModuleNotFoundError` on startup**
Ensure you have run `./scripts/setup.sh` at least once. The Python virtual environment lives at `backend/.venv`. If you switch Python versions, delete the `.venv` directory and re-run setup.

**Frontend shows a blank page or network errors**
Confirm the backend is running (`curl http://localhost:8000/health`) and that `VITE_API_BASE_URL` in your `.env` (or Vite config) matches the backend address.

---

## Architecture Overview

The platform follows a supervisor-orchestrated, specialist-agent design. A central `Supervisor` class routes domain events to the appropriate specialist agent, assembles shared customer context, enforces HITL policy (no agent may act autonomously on customer accounts), and manages inter-agent handoffs — for example, escalating a high-risk fraud signal to the advisory agent to suppress outbound cross-sell. The infrastructure layer is fully abstracted behind interfaces, making it straightforward to swap Couchbase for another datastore or Capella Model Service for a different LLM provider. For a detailed walkthrough of the agent graph, data flow, RBAC model, and deployment topology, see [`docs/architecture.md`](docs/architecture.md).
