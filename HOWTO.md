# Local Setup and Developer Guide

This guide walks through setting up the FinTech Agentic Banking Platform on your local machine, running the agent workflows end-to-end, and extending the system with new agents.

---

## 1. Prerequisites

| Requirement | Minimum version | Notes |
|---|---|---|
| Python | 3.11 | `python3 --version` to check |
| Node.js | 20 LTS | `node --version` to check |
| npm | 9+ | Bundled with Node 20 |
| git | any recent | For cloning the repo |
| Couchbase Capella account | — | Optional. The platform works fully offline with the in-memory adapter. |

No Docker is required for local development.

---

## 2. Clone and Configure

### Clone the repository

```bash
git clone <repository-url> FinTech-Agentic-App
cd FinTech-Agentic-App
```

### Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` in your editor. The table below explains which variables are required vs. optional for each tier.

| Variable | Local dev | With Couchbase | With Capella AI |
|---|---|---|---|
| `APP_ENV` | Set to `development` | `development` or `staging` | any |
| `APP_SECRET_KEY` | Use the default placeholder | Change to a strong random string | Change to a strong random string |
| `COUCHBASE_CONNECTION_STRING` | Leave blank | **Required** — `couchbases://cb.<id>.cloud.couchbase.com` | **Required** |
| `COUCHBASE_USERNAME` | Leave blank | **Required** | **Required** |
| `COUCHBASE_PASSWORD` | Leave blank | **Required** | **Required** |
| `CAPELLA_AI_ENDPOINT` | Leave blank | Leave blank | **Required** — base URL of the Capella Model Service |
| `CAPELLA_AI_API_KEY` | Leave blank | Leave blank | **Required** |
| `OPENAI_API_KEY` | Optional | Optional | Fallback if Capella is unavailable |

**When `COUCHBASE_CONNECTION_STRING` is empty**, the platform selects the in-memory persistence adapter automatically. All five agent workflows are fully functional; data is reset when the server restarts.

**When both `CAPELLA_AI_ENDPOINT` and `OPENAI_API_KEY` are empty**, a stub LLM is used that returns deterministic placeholder responses. This is sufficient for verifying API contracts and running tests.

### Minimal `.env` for offline development

```dotenv
APP_ENV=development
APP_SECRET_KEY=local-dev-only-change-me
# All other variables left blank — in-memory + stub adapters will be selected
```

---

## 3. Setup and Run

### Bootstrap the environment

```bash
./scripts/setup.sh
```

This script does the following in order:

1. Copies `.env.example` to `.env` if no `.env` file exists yet.
2. Creates a Python virtual environment at `backend/.venv`.
3. Upgrades pip and installs the backend package in editable mode with all dev dependencies (`pip install -e ".[dev]"`).
4. Runs `npm install` in `frontend/` to install all Node packages.
5. Marks all scripts in `scripts/` as executable.

You only need to run `setup.sh` once (or again after a clean checkout or Python version change).

### Start the development servers

```bash
./scripts/dev.sh
```

This starts two processes concurrently:

- **Backend** — Uvicorn with hot-reload on `http://localhost:8000`
- **Frontend** — Vite dev server on `http://localhost:5173`

Press `Ctrl+C` to stop both servers.

| Endpoint | URL |
|---|---|
| React frontend | http://localhost:5173 |
| FastAPI backend | http://localhost:8000 |
| Interactive API docs (Swagger) | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health check | http://localhost:8000/health |

---

## 4. Seed Sample Data

```bash
./scripts/seed.sh
```

The seeder calls `python -m app.scripts.seed_data` against the configured backend (Couchbase or in-memory). It creates the following records:

| Type | Count | Details |
|---|---|---|
| Customers | 3 | Asha Mehta (`C-ASHA001`), James Okafor (`C-JAMES002`), Sara Mehta (`C-SARA003`) |
| Households | 1 | `H-001` linking Asha and Sara Mehta |
| Transactions | 3 | Including one flagged transaction (`T-001`, $4,200.55) to exercise the fraud workflow |
| Customer interactions | 2 | Call/chat transcripts for sentiment analysis |
| Loan applications | 1 | Personal loan `L-001` for Asha Mehta ($25,000, incomplete docs) |
| Branch KPIs | 7 | Daily KPI records for `BR-WEST01` (West Side Branch), showing increasing wait times and declining new accounts |

To preview what would be seeded without writing any data:

```bash
cd backend && .venv/bin/python -m app.scripts.seed_data --dry-run
```

---

## 5. How to Run Key Workflows

All API calls below require a bearer token. In development mode, obtain one from the dev-token endpoint. In production, tokens are issued by your configured OIDC provider.

### Obtain a development token

```bash
curl -s -X POST http://localhost:8000/api/auth/dev-token \
  -H "Content-Type: application/json" \
  -d '{"user_id": "dev-user-01", "roles": ["admin"]}' | jq .
```

Response:
```json
{ "access_token": "<jwt>" }
```

Store the token:
```bash
TOKEN="<paste token here>"
```

The dev-token endpoint is disabled in `staging` and `production` environments.

---

### Fraud Triage Workflow

**Step 1 — Ingest a transaction and trigger fraud analysis**

```bash
curl -s -X POST http://localhost:8000/api/fraud/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "txn_id": "T-DEMO-001",
    "customer_id": "C-ASHA001",
    "account_id": "A-1001",
    "amount": 9800.00,
    "currency": "USD",
    "merchant": "WIRE_TRANSFER_INTL",
    "channel": "online",
    "device_id": "D-NEW-99"
  }' | jq .
```

If the risk score warrants an alert, the response includes `alert_id`, `risk_score`, `risk_level`, and `ai_explanation`.

**Step 2 — List pending fraud alerts**

```bash
curl -s http://localhost:8000/api/fraud/alerts \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Step 3 — Approve or escalate an alert (HITL gate)**

```bash
ALERT_ID="<alert_id from step 1>"

curl -s -X POST "http://localhost:8000/api/fraud/alerts/$ALERT_ID/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve", "analyst_notes": "Verified with customer — legitimate transfer"}' | jq .
```

---

### Loan Review Workflow

**Step 1 — Submit a loan application**

```bash
curl -s -X POST http://localhost:8000/api/loans/applications \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "C-JAMES002",
    "loan_type": "personal",
    "requested_amount": 15000.00,
    "term_months": 36,
    "stated_income": 95000.00,
    "stated_employment": "Product Manager",
    "credit_score": 740,
    "submitted_docs": ["paystub", "bank_statement", "id_doc"]
  }' | jq .
```

Note the `application_id` in the response.

**Step 2 — Retrieve the automated review**

```bash
APP_ID="<application_id from step 1>"

curl -s "http://localhost:8000/api/loans/applications/$APP_ID/review" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

The review includes document completeness flags, a DTI assessment, risk signals, and the agent's recommendation.

**Step 3 — Submit underwriter decision (HITL gate)**

```bash
REVIEW_ID="<review_id from step 2>"

curl -s -X POST "http://localhost:8000/api/loans/applications/$APP_ID/decision" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decision": "approved", "underwriter_notes": "Strong profile, all docs verified", "review_id": "'$REVIEW_ID'"}' | jq .
```

---

### Financial Advisory Workflow

**Step 1 — Generate an advice draft**

```bash
curl -s "http://localhost:8000/api/advisory/customers/C-ASHA001/recommendations" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

The draft includes `next_best_actions`, `goals_summary`, `service_sentiment_note`, and `full_advice_text`. If the customer has a negative sentiment signal, `suppress_cross_sell` will be `true`.

**Step 2 — Approve the draft (HITL gate)**

```bash
DRAFT_ID="<draft_id from step 1>"

curl -s -X POST "http://localhost:8000/api/advisory/recommendations/$DRAFT_ID/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"advisor_id": "advisor-001", "advisor_notes": "Reviewed and appropriate for client"}' | jq .
```

---

### Branch Analysis Workflow

**Trigger an analysis run for a branch**

```bash
curl -s -X POST http://localhost:8000/api/branches/BR-WEST01/analyze \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Retrieve generated insights**

```bash
curl -s "http://localhost:8000/api/branches/BR-WEST01/insights" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

The insights include `issue_summary`, `probable_causes`, and `ranked_recommendations` based on the KPI trend data.

---

## 6. Validating Integrations

### Health check

```bash
curl -s http://localhost:8000/health | jq .
# Expected: {"status": "ok", "env": "development"}
```

### Couchbase connectivity

Set the three Couchbase variables in `.env`, restart the backend, and check the startup logs:

```
==> Connected to Couchbase backend: couchbases://cb.<id>.cloud.couchbase.com
```

If the connection fails, the server logs the error and falls back to the in-memory adapter rather than crashing.

### AI service connectivity

Set `CAPELLA_AI_ENDPOINT` and `CAPELLA_AI_API_KEY` (or `OPENAI_API_KEY`) in `.env` and restart. Submit a transaction or request an advice draft. The backend logs will show:

```
LLM call completed  model=gpt-4o  prompt_tokens=412  completion_tokens=185  latency_ms=1840
```

If no AI credentials are configured you will see:

```
Using StubLLMService — set CAPELLA_AI_ENDPOINT or OPENAI_API_KEY for real LLM responses
```

---

## 7. Debugging Common Issues

### Check the health endpoint first

```bash
curl http://localhost:8000/health
```

A `connection refused` response means the backend process is not running. Check terminal output from `./scripts/dev.sh`.

### Read structured logs

The backend emits JSON-structured logs to stdout. Filter by level:

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload 2>&1 | grep '"level":"ERROR"'
```

### Confirm `APP_ENV`

```bash
curl -s http://localhost:8000/health | jq .env
```

If this returns `"test"` or `"production"` unexpectedly, check your `.env` file and ensure there are no conflicting environment variables exported in your shell.

### `422 Unprocessable Entity` responses

These indicate a Pydantic validation error. The response body contains a `detail` array listing each failing field. Check that your request payload matches the schema shown in `/docs`.

### `401 Unauthorized` or `403 Forbidden`

Confirm your token is included in the `Authorization: Bearer <token>` header and has not expired (default TTL is 60 minutes). Re-issue a dev token with the correct roles for the endpoint you are calling.

### Frontend cannot reach the backend

Verify `VITE_API_BASE_URL` in your environment matches the backend URL, or check `frontend/src/services/api.ts` for the hardcoded base URL. Ensure the CORS `FRONTEND_ORIGIN` variable in `.env` matches the Vite dev server origin.

---

## 8. Extending the System — Adding a New Agent

The platform is designed for straightforward extension. Follow these four steps to add a new specialist agent.

### Step 1 — Implement `BaseAgent`

Create `backend/app/application/agents/my_agent.py`:

```python
from app.application.agents.base import BaseAgent
from app.domain.models import MyDomainModel  # define in domain/models/

class MyAgent(BaseAgent):
    name = "my_agent"

    async def analyze(self, subject: MyDomainModel, session_id: str) -> MyResult:
        context = await self._retrieve_context(f"relevant query about {subject.id}")
        prompt = self._build_prompt(subject, context)
        raw = await self._complete(
            messages=[{"role": "user", "content": prompt}],
            session_id=session_id,
            step_index=0,
        )
        result = self._parse_result(raw, subject)
        await self._emit_audit(
            event_id=new_audit_id(),
            action=AuditAction.AGENT_ANALYSIS,
            actor_id=self.name,
            related_object_id=subject.id,
            related_object_type="my_domain_model",
        )
        return result
```

Export the new class from `backend/app/application/agents/__init__.py`.

### Step 2 — Wire it into `container.py`

Open `backend/app/core/container.py` and add construction of your agent alongside the existing specialists:

```python
from app.application.agents.my_agent import MyAgent

# Inside Container.__init__ or a dedicated _init_agents() method:
self.my_agent = MyAgent(
    llm=self.llm,
    retrieval=self.retrieval,
    audit_repo=self.audit,
    trace_repo=self.traces,
)
```

### Step 3 — Add a router

Create `backend/app/api/routers/my_domain.py` with FastAPI route handlers, following the pattern in `fraud.py` or `loans.py`. Register it in `backend/app/main.py`:

```python
from app.api.routers import my_domain
app.include_router(my_domain.router)
```

### Step 4 — Add tests

Create `backend/tests/unit/test_my_agent.py` and `backend/tests/integration/test_my_domain_api.py`. Use the `InMemory*` repositories from `app.infrastructure.persistence.memory` to keep tests fast and dependency-free.

---

## 9. Running Tests

### Full test suite (backend + frontend)

```bash
./scripts/test.sh
```

### Backend tests only

```bash
cd backend && .venv/bin/pytest tests/ -v
```

### Backend tests with coverage report

```bash
cd backend && .venv/bin/pytest tests/ -v --cov=app --cov-report=term-missing
```

### Run a specific test file or test

```bash
cd backend && .venv/bin/pytest tests/unit/test_fraud_agent.py -v
cd backend && .venv/bin/pytest tests/ -v -k "test_fraud"
```

### Frontend tests

```bash
cd frontend && npm test
```

Tests are configured via `pyproject.toml` (`[tool.pytest.ini_options]`). `asyncio_mode = "auto"` means all `async def test_*` functions are automatically treated as async tests. The in-memory persistence adapters are used for all tests; no external services are required.
