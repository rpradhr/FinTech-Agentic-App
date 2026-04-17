# Integration Specification

**FinTech Agentic Banking Platform**
Version 0.1.0 — April 2026

---

## Table of Contents

1. [Internal Integrations](#1-internal-integrations)
2. [External Integrations](#2-external-integrations)
3. [API Contract](#3-api-contract)
4. [Datastore Integration Details](#4-datastore-integration-details)
5. [Auth and RBAC Integration](#5-auth-and-rbac-integration)
6. [Failure Modes and Validation Checklist](#6-failure-modes-and-validation-checklist)

---

## 1. Internal Integrations

### 1.1 Supervisor → Agents

The `Supervisor` class (`backend/app/application/orchestrator.py`) is the sole entry point for all AI-driven workflows. It owns routing, case creation, and the human-in-the-loop enforcement policy. It never takes autonomous actions — it produces artifacts for human review only.

Every call into the Supervisor mints a `session_id` via `new_session_id()` (prefix `SES-`). That ID is passed through the full agent call chain and written into every `AgentTrace` and `AuditEvent` produced during the request, enabling end-to-end trace reconstruction per session.

| Supervisor Method | Agent Called | Trigger | Returns | Case Opened? |
|---|---|---|---|---|
| `process_transaction(txn)` | `FraudAgent.analyze_transaction()` | POST /api/fraud/events | `FraudAlert` | Yes, if risk_level is HIGH or CRITICAL |
| `process_interaction(interaction)` | `SentimentAgent.analyze_interaction()` | POST /api/interactions/analyze | None (side effects only) | Yes, if escalation_recommended |
| `process_loan_application(application)` | `LoanAgent.review_application()` | POST /api/loans/applications | `LoanReview` | Always |
| `analyze_branch(branch_id)` | `BranchAgent.analyze_branch()` | POST /api/branches/{id}/analyze | `BranchInsight` or None | No |
| `generate_advice(customer_id)` | `AdvisoryAgent.generate_advice_draft()` | GET /api/advisory/customers/{id}/recommendations | `AdviceDraft` | No |

**Session ID threading:** Each `session_id` is passed to `BaseAgent._complete()` as a parameter and stored on every `AgentTrace` row written to the `agent_traces` collection. All `AuditEvent` records emitted within the same agent invocation also carry `agent_session_id`. This allows a compliance reviewer to reconstruct the complete agent reasoning path for any decision by querying `GET /api/audit/{object_id}` or by querying `audit.events` directly on the session ID.

**`build_supervisor(container)` function:** Route handlers call this factory at request time, receiving a fully-wired `Supervisor` with all agents and repositories resolved from the container singleton. There is no persistent per-request Supervisor state.

### 1.2 Agents → Repositories

Each specialist agent is injected with only the repositories it needs. The full dependency matrix is:

| Agent | Repositories Injected |
|---|---|
| `FraudAgent` | `FraudRepository`, `TransactionRepository`, `CustomerRepository`, `AuditRepository`, `TraceRepository` |
| `SentimentAgent` | `InteractionRepository`, `CustomerRepository`, `AuditRepository`, `TraceRepository` |
| `LoanAgent` | `LoanRepository`, `CustomerRepository`, `FraudRepository`, `AuditRepository`, `TraceRepository` |
| `BranchAgent` | `BranchRepository`, `InteractionRepository`, `TransactionRepository`, `AuditRepository`, `TraceRepository` |
| `AdvisoryAgent` | `AdvisoryRepository`, `CustomerRepository`, `FraudRepository`, `LoanRepository`, `CaseRepository`, `AuditRepository`, `TraceRepository` |

All repositories are accessed through the abstract interfaces in `backend/app/infrastructure/persistence/interfaces.py`. Agents never import concrete Couchbase or in-memory classes directly.

### 1.3 Agents → AI Services

All agents extend `BaseAgent` (`backend/app/application/agents/base.py`), which provides two AI service entry points:

**`_complete(messages, session_id, step_index, tools, temperature, max_tokens) → str`**

Calls `LLMService.complete()` (either `CapellaLLMService` or `StubLLMService`), then writes an `AgentTrace` record with the following fields captured automatically: `trace_id`, `session_id`, `agent_name`, `step_type="llm_call"`, `step_index`, truncated input messages (200 chars), truncated output content (500 chars), `model_id`, `prompt_tokens`, `completion_tokens`, and `latency_ms`. The trace is persisted via `TraceRepository.append_trace()`.

**`_retrieve_context(query, collection, top_k) → str`**

Calls `RetrievalService.search()` (either `CapellaRetrievalService` or `StubRetrievalService`). Embeds the query string via `EmbeddingService.embed()`, executes a `VECTOR_DISTANCE` SQL++ query against the `banking-core.knowledge.retrieval_chunks` collection, and returns a formatted multi-chunk string with source attribution. Returns an empty string on any retrieval failure so agents degrade gracefully.

**`_emit_audit(event_id, action, actor_id, related_object_id, ...)`**

Constructs an immutable `AuditEvent` (frozen Pydantic model) and calls `AuditRepository.append()`. The `frozen = True` Pydantic config prevents mutation after creation.

### 1.4 Container Wiring

The `Container` class (`backend/app/core/container.py`) is constructed once at startup in `app.main.startup()` and stored as a module-level singleton accessible via `get_container()`.

**Backend selection logic (`Settings.database_backend` property):**

```
APP_ENV == "test"              → DatabaseBackend.MEMORY  (always, test isolation)
COUCHBASE_CONNECTION_STRING set → DatabaseBackend.COUCHBASE
otherwise                      → DatabaseBackend.MEMORY  (dev default)
```

**AI backend selection logic (`Container._init_ai()`):**

```
CAPELLA_AI_ENDPOINT + CAPELLA_AI_API_KEY both set → CapellaLLMService + CapellaEmbeddingService
OPENAI_API_KEY set (fallback)                     → CapellaLLMService (pointed at OpenAI)
CapellaRetrievalService                           → only wired if Couchbase is also active
otherwise                                         → StubLLMService + StubRetrievalService
```

**Connection lifecycle:**

1. `Container.__init__()` — synchronous; builds all repository and service objects.
2. `await container.connect()` — establishes the async Couchbase cluster connection (runs SDK `Cluster()` constructor in the thread pool executor via `loop.run_in_executor`).
3. `set_container(container)` — stores the singleton; `get_container()` will raise `RuntimeError` if called before this point.
4. `await container.close()` — called in `app.main.shutdown()`.

---

## 2. External Integrations

### 2.1 Couchbase Capella Operational

**Connection setup:**

```python
auth = PasswordAuthenticator(COUCHBASE_USERNAME, COUCHBASE_PASSWORD)
timeout_opts = ClusterTimeoutOptions(
    connect_timeout=10.0,   # seconds
    kv_timeout=5.0,
    query_timeout=30.0,
)
opts = ClusterOptions(auth, timeout_options=timeout_opts)
cluster = Cluster(COUCHBASE_CONNECTION_STRING, opts)
```

The SDK `Cluster()` constructor is synchronous and blocks for DNS resolution and initial bootstrap. It is wrapped with `loop.run_in_executor(None, ...)` to avoid blocking the FastAPI event loop.

**Bucket and Scope/Collection Map:**

Bucket name: `banking-core` (configurable via `COUCHBASE_BUCKET`, default `banking-core`).

| Logical Name (internal key) | Scope | Collection | Primary Owner |
|---|---|---|---|
| `customers` | `customers` | `profiles` | CustomerRepository |
| `households` | `customers` | `households` | CustomerRepository |
| `customer_signals` | `customers` | `preferences` | CustomerRepository |
| `transactions` | `transactions` | `ledger_events` | TransactionRepository |
| `devices` | `transactions` | `devices` | TransactionRepository |
| `fraud_alerts` | `agents` | `recommendations` | FraudRepository |
| `fraud_rings` | `agents` | `case_context` | FraudRepository |
| `loan_applications` | `loans` | `applications` | LoanRepository |
| `loan_reviews` | `loans` | `reviews` | LoanRepository |
| `loan_exceptions` | `loans` | `policy_refs` | LoanRepository |
| `interactions` | `interactions` | `transcripts` | InteractionRepository |
| `interaction_analyses` | `interactions` | `analysis` | InteractionRepository |
| `branch_kpis` | `branches` | `kpis` | BranchRepository |
| `branch_alerts` | `branches` | `alerts` | BranchRepository |
| `branch_insights` | `branches` | `alerts` | BranchRepository |
| `cases` | `agents` | `case_context` | CaseRepository |
| `advice_drafts` | `agents` | `recommendations` | AdvisoryRepository |
| `audit_events` | `audit` | `events` | AuditRepository |
| `agent_traces` | `audit` | `events` | TraceRepository |
| `agent_sessions` | `agents` | `session_state` | RetrievalService (index writes) |

**Executor pattern for async:** Every Couchbase SDK operation is synchronous. The base repository helper `_run_sync(fn, *args)` wraps each call with `loop.run_in_executor(None, lambda: fn(*args))`. This offloads blocking I/O to the default `ThreadPoolExecutor` without blocking the event loop. All repository public methods are `async def` and `await _run_sync(...)`.

**SQL++ query examples:**

```sql
-- Pending fraud alerts by risk score
SELECT f.* FROM `banking-core`.agents.recommendations f
WHERE f.type = 'fraud_alert' AND f.status = 'pending_analyst_review'
ORDER BY f.risk_score DESC LIMIT $lim

-- Recent transactions for a customer
SELECT t.* FROM `banking-core`.transactions.ledger_events t
WHERE t.customer_id = $cid ORDER BY t.event_ts DESC LIMIT $lim

-- Loan review lookup by application
SELECT r.* FROM `banking-core`.loans.reviews r
WHERE r.application_id = $aid LIMIT 1

-- Branch dashboard (latest KPI per branch)
SELECT k.branch_id, k.branch_name, k.report_date,
       k.avg_wait_time_minutes, k.complaint_count, k.new_accounts_opened
FROM `banking-core`.branches.kpis k
WHERE k.report_date = (
  SELECT MAX(k2.report_date) FROM `banking-core`.branches.kpis k2
  WHERE k2.branch_id = k.branch_id
)

-- Audit trail for an object
SELECT e.* FROM `banking-core`.audit.events e
WHERE e.related_object_id = $oid ORDER BY e.ts

-- Open cases filtered by type
SELECT c.* FROM `banking-core`.agents.case_context c
WHERE c.status != 'closed' AND c.case_type = $ct
ORDER BY c.created_at DESC LIMIT $lim
```

Parameters are passed as named `$param` tokens via the Python SDK's `cluster.query(statement, **params)` call.

### 2.2 Capella AI Services

**Model Service (LLM completions):**

The `CapellaLLMService` uses the `openai` Python library pointed at the Capella endpoint, making the integration surface OpenAI-compatible.

| Config Env Var | Purpose | Example |
|---|---|---|
| `CAPELLA_AI_ENDPOINT` | Base URL of the Capella Model Service | `https://api.capella.ai/v1` |
| `CAPELLA_AI_API_KEY` | API key for authentication | `cap-...` |
| `CAPELLA_MODEL_ID` | Default chat completion model | `gpt-4o` |
| `CAPELLA_EMBEDDING_MODEL_ID` | Embedding model | `text-embedding-3-small` |

All completions are called with `temperature=0.2` (low variance for deterministic agent behavior) and `max_tokens=2048` by default. Tool calls use `tool_choice="auto"`.

**Embedding Service:**

`CapellaEmbeddingService.embed(text)` calls `client.embeddings.create(model=..., input=text)` and returns an `EmbeddingResponse(embedding: list[float], model: str, token_count: int)`. Batch embedding via `embed_batch()` sends all texts in a single API call and re-orders results by index.

**Vector Search:**

`CapellaRetrievalService.search(query, collection, top_k, filters)` implements the following pipeline:

1. Embed the query string using `EmbeddingService.embed()`.
2. Execute a SQL++ query using the `VECTOR_DISTANCE` function against `banking-core.knowledge.retrieval_chunks`.
3. Filter by `collection_name` field for logical segmentation.
4. Return up to `top_k` results sorted by cosine similarity score (ascending — lower = closer in Capella's VECTOR_DISTANCE convention).

```sql
SELECT c.chunk_id, c.content, c.source, c.metadata,
       VECTOR_DISTANCE(c.embedding, $vec, 'cosine') AS score
FROM `banking-core`.knowledge.retrieval_chunks c
WHERE c.collection_name = 'fraud_policies'
ORDER BY score LIMIT $topk
```

**Agent Tracer:**

Every `BaseAgent._complete()` call writes an `AgentTrace` document. The `AgentTrace` model (`backend/app/domain/models/audit.py`) aligns with Capella's Agent Tracer structure: `trace_id`, `session_id`, `agent_name`, `step_type` (one of `user`, `internal`, `llm_call`, `tool_call`, `tool_result`, `handoff`, `assistant`), `step_index`, `input_data`, `output_data`, `model_id`, `prompt_tokens`, `completion_tokens`, `latency_ms`, `ts`.

**AI Functions (future — not yet implemented):**

The `banking-core` bucket structure reserves `banking-core.interactions.analysis` for AI-generated sentiment records. Future work includes calling a Capella AI Function for in-database sentiment classification directly from a SQL++ `EXECUTE FUNCTION sentiment_classify(content)` expression, eliminating the round-trip to the application tier.

### 2.3 OIDC/SAML Identity Provider

**JWT validation path:**

In production, the application validates Bearer tokens issued by an external OIDC provider. Tokens are decoded using `jose.jwt.decode()` with `app_secret_key` as the symmetric secret (HS256 algorithm). The `get_current_user()` FastAPI dependency extracts `sub` (user ID) and `roles` (list of role strings) from the payload.

In production deployments with an asymmetric OIDC provider, `jwt_public_key_path` is set to the path of the provider's RSA public key and the algorithm is changed to `RS256`. The `_decode_token()` function must be updated to load the public key for RS256 validation.

**Development token endpoint:**

`POST /api/auth/dev-token` is available only when `APP_ENV` is `development` or `test`. In `staging` and `production`, the endpoint returns HTTP 404 with a generic error (the existence of the endpoint is not revealed).

**Role claims:**

The JWT `roles` field is a JSON array of role string values (see [Section 5](#5-auth-and-rbac-integration) for the full role list). The `require_roles()` dependency factory enforces that the authenticated user holds at least one of the listed roles. The `admin` role bypasses all role checks.

**Production OIDC setup steps:**

1. Register `fintech-agentic-app` as a confidential client in the IdP.
2. Set `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`.
3. Configure the IdP to include a `roles` claim in ID and access tokens.
4. Set `JWT_PUBLIC_KEY_PATH` and update `_decode_token()` to use RS256.
5. Set `APP_ENV=production` — dev-token endpoint becomes unreachable.
6. Rotate `APP_SECRET_KEY` to a cryptographically random 64-character string.

### 2.4 Kafka Event Bus (Optional / Scaffolded)

| Config Env Var | Default | Purpose |
|---|---|---|
| `EVENTING_ENABLED` | `false` | Master switch — no Kafka connections are made if false |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Comma-separated broker list |
| `KAFKA_TRANSACTION_TOPIC` | `banking.transactions` | Inbound transaction stream topic |
| `KAFKA_INTERACTION_TOPIC` | `banking.interactions` | Inbound interaction stream topic |

When `EVENTING_ENABLED=true`, the intended consumer pattern is: a background task consumes messages from `banking.transactions`, deserializes them into `Transaction` domain objects, and calls `supervisor.process_transaction()` — replicating exactly the behavior of the REST ingestion endpoint. The Kafka consumer is scaffolded but not yet implemented. Current ingestion is REST-only.

Downstream event publishing (e.g., emitting `fraud_alert_created` events to downstream systems) is also not yet implemented. The audit log serves as the durable event record in the interim.

### 2.5 OpenTelemetry

| Config Env Var | Default | Purpose |
|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `""` (disabled) | OTLP collector endpoint, e.g. `http://otel-collector:4317` |
| `OTEL_SERVICE_NAME` | `fintech-agentic-app` | Service name reported in traces and metrics |

When `OTEL_EXPORTER_OTLP_ENDPOINT` is set, the `opentelemetry-instrumentation-fastapi` package auto-instruments all HTTP routes, reporting spans to the configured collector. Agent-level traces are captured independently via the `AgentTrace` mechanism (see Section 2.2) and written to Couchbase, not to the OTEL pipeline.

To enable full OTEL integration:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317 \
OTEL_SERVICE_NAME=fintech-agentic-app \
opentelemetry-instrument uvicorn app.main:app
```

---

## 3. API Contract

Base URL: `http://localhost:8000` (development). All endpoints require `Authorization: Bearer <token>` unless noted.

### 3.1 Endpoint Table

| Method | Path | Required Role(s) | Description |
|---|---|---|---|
| POST | `/api/auth/dev-token` | None (dev/test only) | Issue a development JWT |
| POST | `/api/fraud/events` | fraud_analyst, service_account, admin | Ingest transaction and trigger fraud analysis |
| GET | `/api/fraud/alerts` | fraud_analyst, compliance_reviewer | List pending fraud alerts |
| GET | `/api/fraud/alerts/{id}` | fraud_analyst, compliance_reviewer | Get a single fraud alert |
| POST | `/api/fraud/alerts/{id}/approve` | fraud_analyst | Human-in-the-loop: approve/decline/escalate alert |
| POST | `/api/interactions/analyze` | cx_lead, service_account, admin | Ingest interaction and run sentiment analysis |
| GET | `/api/interactions/customers/{id}/signals` | cx_lead, financial_advisor, fraud_analyst, compliance_reviewer | Get aggregated customer sentiment signal |
| POST | `/api/loans/applications` | underwriter, service_account, admin | Submit loan application and trigger automated review |
| GET | `/api/loans/applications/{id}/review` | underwriter, compliance_reviewer | Get automated review for an application |
| POST | `/api/loans/applications/{id}/decision` | underwriter | Human-in-the-loop: record underwriter decision |
| GET | `/api/advisory/customers/{id}/recommendations` | financial_advisor, admin | Generate (or retrieve latest) advice draft |
| POST | `/api/advisory/recommendations/{id}/approve` | financial_advisor | Human-in-the-loop: approve or edit advice draft |
| GET | `/api/branches/dashboard` | branch_manager, admin | Latest KPI snapshot for all branches |
| GET | `/api/branches/{id}/insights` | branch_manager, admin | Recent AI-generated insights for a branch |
| POST | `/api/branches/{id}/analyze` | branch_manager, admin | Trigger on-demand branch analysis |
| GET | `/api/cases/{id}` | fraud_analyst, underwriter, branch_manager, financial_advisor, compliance_reviewer | Get a single case |
| GET | `/api/cases` | compliance_reviewer, admin | List open cases (filter by case_type) |
| GET | `/api/audit/{object_id}` | compliance_reviewer, admin | Full audit trail for any object |
| GET | `/api/metrics/agents` | compliance_reviewer, admin | Agent performance summary counts |
| GET | `/health` | None | Liveness probe |

### 3.2 Request and Response Schemas

**POST /api/auth/dev-token**

```json
// Request
{ "user_id": "analyst-001", "roles": ["fraud_analyst"] }

// Response 200
{ "access_token": "<jwt>", "token_type": "bearer" }
```

```bash
curl -X POST http://localhost:8000/api/auth/dev-token \
  -H "Content-Type: application/json" \
  -d '{"user_id":"analyst-001","roles":["fraud_analyst"]}'
```

---

**POST /api/fraud/events**

```json
// Request
{
  "txn_id": "TXN-ABC123",
  "customer_id": "CUST-001",
  "account_id": "ACC-001",
  "amount": 4500.00,
  "currency": "USD",
  "merchant": "ACME Electronics",
  "channel": "online",
  "device_id": "DEV-XYZ",
  "geo": {"country": "US", "city": "San Francisco"},
  "branch_id": null,
  "event_ts": "2026-04-15T14:30:00Z",
  "metadata": {}
}

// Response 202
{
  "alert_id": "FRAUD-A1B2C3D4",
  "txn_id": "TXN-ABC123",
  "customer_id": "CUST-001",
  "risk_score": 0.87,
  "risk_level": "high",
  "reasons": ["unusual_amount", "new_device", "velocity_breach"],
  "recommended_action": "manual_hold_review",
  "ai_explanation": "Transaction amount 3.2x customer average ...",
  "status": "pending_analyst_review",
  "created_at": "2026-04-15T14:30:05Z"
}
```

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/dev-token \
  -H "Content-Type: application/json" \
  -d '{"user_id":"analyst-001","roles":["fraud_analyst"]}' | jq -r .access_token)

curl -X POST http://localhost:8000/api/fraud/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"txn_id":"TXN-001","customer_id":"CUST-001","account_id":"ACC-001","amount":4500,"currency":"USD","channel":"online"}'
```

---

**POST /api/fraud/alerts/{id}/approve**

```json
// Request
{
  "analyst_id": "analyst-001",
  "decision": "approved",
  "notes": "Confirmed fraudulent — customer contacted."
}
// decision: "approved" | "declined" | "escalated"

// Response 200 — FraudAlertResponse with updated status
```

---

**POST /api/interactions/analyze**

```json
// Request
{
  "interaction_id": null,
  "customer_id": "CUST-001",
  "source": "phone_call",
  "content": "I've been waiting 20 minutes and nobody has helped me ...",
  "branch_id": "BR-01",
  "channel_metadata": {"call_id": "CALL-789", "duration_seconds": 185}
}

// Response 202
{ "message": "Interaction analyzed", "interaction_id": "INT-XXXXXXXX" }
```

---

**POST /api/loans/applications**

```json
// Request
{
  "customer_id": "CUST-001",
  "loan_type": "personal",
  "requested_amount": 25000.00,
  "term_months": 60,
  "stated_income": 85000.00,
  "stated_employment": "Software Engineer at Acme Corp",
  "credit_score": 720,
  "submitted_docs": ["pay_stub_2026_03", "tax_return_2025"]
}

// Response 202
{
  "message": "Application submitted and review started",
  "application_id": "L-XXXXXXXXXXXXXXXX",
  "review_id": "REV-XXXXXXXXXXXXXXXX"
}
```

```bash
curl -X POST http://localhost:8000/api/loans/applications \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"CUST-001","loan_type":"personal","requested_amount":25000,"term_months":60,"stated_income":85000,"credit_score":720,"submitted_docs":[]}'
```

---

**POST /api/loans/applications/{id}/decision**

```json
// Request
{
  "underwriter_id": "uw-jane-doe",
  "decision": "approved",
  "notes": "DTI within policy, stable employment confirmed."
}
// decision: "approved" | "conditionally_approved" | "declined" | "pending_documents"

// Response 200 — LoanReviewResponse with updated underwriter_decision
```

---

**GET /api/advisory/customers/{id}/recommendations**

Query params: `advisor_id` (optional string)

```json
// Response 200
{
  "draft_id": "ADV-XXXXXXXXXXXXXXXX",
  "customer_id": "CUST-001",
  "advisor_id": "advisor-alice",
  "next_best_actions": [
    {"action": "rebalance_portfolio", "rationale": "...", "priority": 1}
  ],
  "customer_context_summary": "Long-standing customer, moderate risk ...",
  "goals_summary": "Retirement in 12 years, home purchase in 3 ...",
  "service_sentiment_note": "Recent complaint resolved — approach with empathy.",
  "suppress_cross_sell": false,
  "full_advice_text": "Based on your current portfolio ...",
  "status": "draft",
  "created_at": "2026-04-15T14:35:00Z"
}
```

---

**GET /api/audit/{object_id}**

Returns an ordered list of `AuditEventResponse` objects for any entity ID (alert, review, draft, case).

```bash
curl http://localhost:8000/api/audit/FRAUD-A1B2C3D4 \
  -H "Authorization: Bearer $TOKEN"
```

```json
[
  {
    "event_id": "AUD-XXXXXXXXXXXXXXXX",
    "actor_type": "agent",
    "actor_id": "fraud_agent",
    "action": "fraud_alert_created",
    "related_object_id": "FRAUD-A1B2C3D4",
    "related_object_type": "fraud_alert",
    "customer_id": "CUST-001",
    "notes": null,
    "ts": "2026-04-15T14:30:05Z"
  },
  {
    "event_id": "AUD-YYYYYYYYYYYYYYYY",
    "actor_type": "human",
    "actor_id": "analyst-001",
    "action": "fraud_alert_approved",
    "related_object_id": "FRAUD-A1B2C3D4",
    "related_object_type": "fraud_alert",
    "customer_id": "CUST-001",
    "notes": "Confirmed fraudulent — customer contacted.",
    "ts": "2026-04-15T14:45:00Z"
  }
]
```

---

**GET /health**

```json
{ "status": "ok", "env": "production" }
```

No auth required. Suitable for load balancer health probes.

---

## 4. Datastore Integration Details

### 4.1 Collection Ownership Table

| Collection (Logical) | Scope.Collection | Reads | Writes |
|---|---|---|---|
| `customers` | customers.profiles | FraudAgent, LoanAgent, SentimentAgent, AdvisoryAgent, BranchAgent | SeedData, CustomerRepository |
| `households` | customers.households | AdvisoryAgent | CustomerRepository |
| `customer_signals` | customers.preferences | AdvisoryAgent | SentimentAgent (via CustomerRepository) |
| `transactions` | transactions.ledger_events | FraudAgent, BranchAgent | /api/fraud/events ingest handler |
| `devices` | transactions.devices | FraudAgent | TransactionRepository |
| `fraud_alerts` | agents.recommendations | FraudAgent, AdvisoryAgent, LoanAgent | FraudAgent |
| `fraud_rings` | agents.case_context | FraudAgent | FraudAgent |
| `loan_applications` | loans.applications | LoanAgent | /api/loans/applications ingest handler |
| `loan_reviews` | loans.reviews | LoanAgent, /api/loans endpoint | LoanAgent |
| `loan_exceptions` | loans.policy_refs | LoanAgent | LoanAgent |
| `interactions` | interactions.transcripts | SentimentAgent, BranchAgent | /api/interactions/analyze ingest handler |
| `interaction_analyses` | interactions.analysis | AdvisoryAgent | SentimentAgent |
| `branch_kpis` | branches.kpis | BranchAgent, /api/branches/dashboard | BranchRepository |
| `branch_alerts` | branches.alerts | BranchAgent | BranchAgent |
| `branch_insights` | branches.alerts | /api/branches/{id}/insights | BranchAgent |
| `cases` | agents.case_context | AdvisoryAgent, /api/cases | Supervisor._open_case() |
| `advice_drafts` | agents.recommendations | /api/advisory | AdvisoryAgent |
| `audit_events` | audit.events | /api/audit | All agents via BaseAgent._emit_audit() |
| `agent_traces` | audit.events | /api/metrics/agents | All agents via BaseAgent._complete() |
| `agent_sessions` | agents.session_state | — | CapellaRetrievalService.index_chunk() |
| `retrieval_chunks` | knowledge.retrieval_chunks | CapellaRetrievalService | Offline indexing pipeline |

### 4.2 Index Requirements for Production

Create these indexes before go-live. All GSI indexes are on the `banking-core` bucket.

| Index Name | Target Collection | Fields Indexed | Purpose |
|---|---|---|---|
| `idx_transactions_customer` | transactions.ledger_events | `customer_id`, `event_ts DESC` | Customer transaction history queries |
| `idx_transactions_account` | transactions.ledger_events | `account_id`, `event_ts DESC` | Account statement queries |
| `idx_transactions_device` | transactions.ledger_events | `device_id`, `event_ts DESC` | Device velocity checks |
| `idx_transactions_merchant` | transactions.ledger_events | `merchant`, `event_ts DESC` | Merchant pattern queries |
| `idx_transactions_branch_flagged` | transactions.ledger_events | `branch_id`, `status`, `event_ts` | Branch flagged transaction queries |
| `idx_fraud_alerts_status` | agents.recommendations | `type`, `status`, `risk_score DESC` | Pending alert queue |
| `idx_fraud_alerts_customer` | agents.recommendations | `type`, `customer_id`, `created_at DESC` | Customer fraud history |
| `idx_loan_reviews_application` | loans.reviews | `application_id` | Review lookup by application |
| `idx_loan_reviews_pending` | loans.reviews | `underwriter_decision`, `created_at DESC` | Pending review queue |
| `idx_loan_exceptions_application` | loans.policy_refs | `application_id` | Exception lookup |
| `idx_interactions_customer` | interactions.transcripts | `customer_id`, `created_at DESC` | Customer interaction history |
| `idx_analysis_interaction` | interactions.analysis | `interaction_id` | Analysis lookup |
| `idx_analysis_customer` | interactions.analysis | `customer_id`, `created_at DESC` | Customer analysis history |
| `idx_branch_kpis_branch_date` | branches.kpis | `branch_id`, `report_date DESC` | KPI history and dashboard |
| `idx_branch_alerts_branch` | branches.alerts | `branch_id`, `created_at DESC` | Branch alert/insight queries |
| `idx_cases_status_type` | agents.case_context | `status`, `case_type`, `created_at DESC` | Open case queue |
| `idx_cases_customer` | agents.case_context | `customer_id`, `created_at DESC` | Customer case history |
| `idx_audit_object` | audit.events | `related_object_id`, `ts` | Audit trail lookup |
| `idx_audit_customer` | audit.events | `customer_id`, `ts DESC` | Customer audit history |
| `idx_audit_session` | audit.events | `agent_session_id`, `ts` | Session trace reconstruction |
| `idx_chunks_collection` | knowledge.retrieval_chunks | `collection_name` | Pre-filter before vector search |
| **vector** `idx_chunks_embedding` | knowledge.retrieval_chunks | `embedding` (1536-dim, cosine) | VECTOR_DISTANCE queries |

**Vector index configuration** (Capella UI or REST API):

```json
{
  "name": "banking-vector-index",
  "type": "fulltext-index",
  "params": {
    "mapping": {
      "types": {
        "knowledge.retrieval_chunks": {
          "properties": {
            "embedding": {
              "fields": [{ "type": "vector", "dims": 1536, "similarity": "dot_product" }]
            }
          }
        }
      }
    }
  }
}
```

### 4.3 Document Key Conventions

All document keys follow the pattern `<PREFIX><16-char-uppercase-hex>`. The prefix makes collection routing, log scanning, and support tickets immediately clear.

| Entity | Key Prefix | Example |
|---|---|---|
| Audit Event | `AUD-` | `AUD-A1B2C3D4E5F60708` |
| Fraud Alert | `FRAUD-` | `FRAUD-A1B2C3D4E5F60708` |
| Loan Application | `L-` | `L-A1B2C3D4E5F60708` |
| Loan Review | `REV-` | `REV-A1B2C3D4E5F60708` |
| Case | `CASE-` | `CASE-A1B2C3D4E5F60708` |
| Advice Draft | `ADV-` | `ADV-A1B2C3D4E5F60708` |
| Agent Trace | `TRC-` | `TRC-A1B2C3D4E5F60708` |
| Session | `SES-` | `SES-A1B2C3D4E5F60708` |
| Interaction | `INT-` | `INT-A1B2C3D4E5F60708` |
| Interaction Analysis | `ANA-` | `ANA-A1B2C3D4E5F60708` |
| Branch Insight | `BRN-` | `BRN-A1B2C3D4E5F60708` |
| Customer (external) | none (raw ID) | `CUST-001` |
| Transaction (external) | none (raw ID) | `TXN-ABC123` |

### 4.4 Known Query Patterns and Their SQL++ Forms

| Pattern | SQL++ |
|---|---|
| Get pending fraud alerts | `SELECT f.* FROM banking-core.agents.recommendations f WHERE f.type='fraud_alert' AND f.status='pending_analyst_review' ORDER BY f.risk_score DESC LIMIT $lim` |
| Get customer recent transactions | `SELECT t.* FROM banking-core.transactions.ledger_events t WHERE t.customer_id=$cid ORDER BY t.event_ts DESC LIMIT $lim` |
| Get household members | `SELECT c.* FROM banking-core.customers.profiles c WHERE c.household_id=$hid` |
| Get loan review for application | `SELECT r.* FROM banking-core.loans.reviews r WHERE r.application_id=$aid LIMIT 1` |
| Get pending loan reviews | `SELECT r.* FROM banking-core.loans.reviews r WHERE r.underwriter_decision IS MISSING OR r.underwriter_decision IS NULL ORDER BY r.created_at DESC LIMIT $lim` |
| Get open cases | `SELECT c.* FROM banking-core.agents.case_context c WHERE c.status != 'closed' ORDER BY c.created_at DESC LIMIT $lim` |
| Get audit trail for object | `SELECT e.* FROM banking-core.audit.events e WHERE e.related_object_id=$oid ORDER BY e.ts` |
| Get trace steps for session | `SELECT t.* FROM banking-core.audit.events t WHERE t.session_id=$sid ORDER BY t.step_index` |
| Branch KPI latest | Correlated subquery selecting `MAX(report_date)` per `branch_id` (see Section 2.1) |
| Vector similarity search | `SELECT ... VECTOR_DISTANCE(c.embedding, $vec, 'cosine') AS score FROM banking-core.knowledge.retrieval_chunks c WHERE c.collection_name=$col ORDER BY score LIMIT $topk` |

---

## 5. Auth and RBAC Integration

### 5.1 JWT Claims Structure

All tokens carry the following claims:

| Claim | Type | Description |
|---|---|---|
| `sub` | string | User identifier (maps to `CurrentUser.user_id`) |
| `roles` | string[] | Array of role string values (see below) |
| `exp` | integer (Unix) | Expiry timestamp — default TTL is `JWT_EXPIRE_MINUTES` (60 min) |
| `iat` | integer (Unix) | Issued-at timestamp |

Example decoded payload:

```json
{
  "sub": "analyst-001",
  "roles": ["fraud_analyst"],
  "exp": 1744737600,
  "iat": 1744734000
}
```

### 5.2 Role Definitions

| Role Value | Description |
|---|---|
| `fraud_analyst` | Reviews and acts on fraud alerts |
| `underwriter` | Reviews and decides on loan applications |
| `branch_manager` | Views branch KPIs and triggers branch analysis |
| `cx_lead` | Submits customer interactions for sentiment analysis |
| `financial_advisor` | Generates and approves advice drafts |
| `compliance_reviewer` | Read-only access to cases, audit trails, and metrics |
| `admin` | Bypasses all role checks; full access |
| `service_account` | Used by backend services for automated event ingestion |

### 5.3 Role → Allowed Endpoints Matrix

| Endpoint | fraud_analyst | underwriter | branch_manager | cx_lead | financial_advisor | compliance_reviewer | admin | service_account |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| POST /api/fraud/events | Y | | | | | | Y | Y |
| GET /api/fraud/alerts | Y | | | | | Y | Y | |
| GET /api/fraud/alerts/{id} | Y | | | | | Y | Y | |
| POST /api/fraud/alerts/{id}/approve | Y | | | | | | Y | |
| POST /api/interactions/analyze | | | | Y | | | Y | Y |
| GET /api/interactions/customers/{id}/signals | Y | | | Y | Y | Y | Y | |
| POST /api/loans/applications | | Y | | | | | Y | Y |
| GET /api/loans/applications/{id}/review | | Y | | | | Y | Y | |
| POST /api/loans/applications/{id}/decision | | Y | | | | | Y | |
| GET /api/advisory/customers/{id}/recommendations | | | | | Y | | Y | |
| POST /api/advisory/recommendations/{id}/approve | | | | | Y | | Y | |
| GET /api/branches/dashboard | | | Y | | | | Y | |
| GET /api/branches/{id}/insights | | | Y | | | | Y | |
| POST /api/branches/{id}/analyze | | | Y | | | | Y | |
| GET /api/cases/{id} | Y | Y | Y | | Y | Y | Y | |
| GET /api/cases | | | | | | Y | Y | |
| GET /api/audit/{object_id} | | | | | | Y | Y | |
| GET /api/metrics/agents | | | | | | Y | Y | |
| GET /health | Y | Y | Y | Y | Y | Y | Y | Y |

### 5.4 Production OIDC Setup Steps

1. Provision an OIDC-compliant IdP (e.g., Keycloak, Auth0, Azure AD B2C, Okta).
2. Create a client named `fintech-agentic-app` with:
   - Client authentication: confidential
   - Allowed redirect URIs: `https://<frontend-domain>/auth/callback`
   - Token signing: RS256 preferred
3. Create groups or roles in the IdP matching the role values in Section 5.2.
4. Configure the IdP to embed role membership as a `roles` claim in the access token.
5. Set environment variables:
   ```
   OIDC_ISSUER_URL=https://your-idp.example.com/realms/fintech
   OIDC_CLIENT_ID=fintech-agentic-app
   OIDC_CLIENT_SECRET=<secret>
   JWT_PUBLIC_KEY_PATH=/etc/ssl/jwt/public_key.pem
   APP_SECRET_KEY=<64-char random string>
   APP_ENV=production
   ```
6. Update `_decode_token()` in `backend/app/api/auth.py` to load the public key and use `algorithm="RS256"`.
7. Verify that `APP_ENV=production` — the dev-token endpoint returns 404.
8. Smoke-test by requesting a token from the IdP's token endpoint and calling `GET /api/fraud/alerts` with it.

---

## 6. Failure Modes and Validation Checklist

### 6.1 Failure Modes by Integration

| Integration | Failure Scenario | Degraded Behavior | Recovery |
|---|---|---|---|
| Couchbase (connection loss) | `CouchbaseException` on `connect()` at startup | Application fails to start — `container.connect()` raises, startup event aborts, FastAPI does not bind | Fix connectivity; restart process |
| Couchbase (query timeout) | Individual query exceeds `query_timeout=30s` | Repository method raises exception; FastAPI global handler returns HTTP 500; agent workflow fails; no partial write | Alert on 500 rate; check Couchbase cluster health |
| Couchbase (document not found) | `DocumentNotFoundException` on `.get()` | `_BaseRepo._get()` returns `None`; agents handle missing context gracefully (empty profile, no prior alerts) | Investigate missing seed data |
| Capella AI / LLM (unreachable) | HTTP error from OpenAI-compatible endpoint | `CapellaLLMService.complete()` raises; agent workflow fails; HTTP 500 returned to caller | Fall back to `StubLLMService` by unsetting `CAPELLA_AI_ENDPOINT`; set `OPENAI_API_KEY` for direct OpenAI access |
| Capella AI / LLM (malformed JSON) | LLM returns non-parseable JSON | `FraudAgent._parse_assessment()` catches `Exception`, logs a warning, returns a safe default (`risk_score=0.5`, `risk_level="medium"`, `action="manual_hold_review"`) | Alert on `parsing_error` in reasons field; tune prompt |
| Vector search (index missing) | `VECTOR_DISTANCE` query fails | `CapellaRetrievalService.search()` catches `Exception`, logs warning, returns `[]`; `_retrieve_context()` returns `""`; agents proceed without retrieved context | Create vector index per Section 4.2 |
| JWT validation (invalid/expired) | `JWTError` in `_decode_token()` | HTTP 401 with `"Invalid token: ..."` detail | Token refresh; check `APP_SECRET_KEY` rotation |
| JWT validation (OIDC IdP down) | IdP JWKS endpoint unreachable (RS256) | HTTP 401 for all authenticated requests | Ensure IdP HA; consider token caching |
| CORS misconfiguration | Preflight returns wrong origin | Frontend blocked at browser | Update `CORS_ALLOWED_ORIGINS` and restart |
| Kafka consumer (EVENTING_ENABLED=false) | No consumer started | Events processed via REST only — no Kafka consumption | Intentional until consumer is implemented |
| Kafka broker (EVENTING_ENABLED=true) | Broker unreachable | Consumer fails to connect; REST ingestion is unaffected | Check `KAFKA_BOOTSTRAP_SERVERS`; consumer retry logic not yet implemented |
| Container not initialized | `get_container()` called before startup | `RuntimeError: Container not initialized` → HTTP 500 | Ensure lifespan startup event completed before requests arrive; add readiness probe on `/health` |
| Audit repository failure | `AuditRepository.append()` raises | `AuditEvent` not persisted; agent workflow completes but without audit record | Critical — monitor audit write failures; do not suppress in production |

### 6.2 Pre-Go-Live Validation Checklist

#### Couchbase / Data Layer

- [ ] `COUCHBASE_CONNECTION_STRING` resolves and `PasswordAuthenticator` succeeds.
- [ ] Bucket `banking-core` exists with all five scopes: `customers`, `transactions`, `agents`, `loans`, `interactions`, `branches`, `audit`, `knowledge`.
- [ ] All collections listed in Section 4.1 are created.
- [ ] All GSI indexes in Section 4.2 are built (check index state = `online`).
- [ ] Vector index `banking-vector-index` is built and `VECTOR_DISTANCE` returns results.
- [ ] Seed data is loaded and `GET /health` returns `{"status":"ok"}`.
- [ ] Timeout settings (`connect_timeout`, `kv_timeout`, `query_timeout`) are appropriate for network latency to Capella endpoint.

#### AI Services

- [ ] `CAPELLA_AI_ENDPOINT` and `CAPELLA_AI_API_KEY` are set and a test completion request succeeds.
- [ ] `CAPELLA_MODEL_ID` model is accessible under the configured API key.
- [ ] `CAPELLA_EMBEDDING_MODEL_ID` returns embeddings of the expected dimensionality (1536 for `text-embedding-3-small`).
- [ ] At least one knowledge chunk is indexed so `_retrieve_context()` returns non-empty results.
- [ ] Stub mode (`StubLLMService`) can be triggered by clearing `CAPELLA_AI_ENDPOINT` and `OPENAI_API_KEY` for offline testing.

#### Auth and JWT

- [ ] `APP_SECRET_KEY` is a cryptographically random string (minimum 32 characters); default `dev-secret-key-change-in-production` is NOT in use.
- [ ] `APP_ENV=production` — confirm `POST /api/auth/dev-token` returns HTTP 404.
- [ ] Production OIDC flow issues tokens with correct `roles` claim and the backend accepts them.
- [ ] Token expiry (`JWT_EXPIRE_MINUTES`) is set to an appropriate value (recommended: 60 minutes with refresh tokens).
- [ ] `require_roles()` returns HTTP 403 (not 401) when a valid token lacks the required role.

#### CORS and HTTPS

- [ ] `CORS_ALLOWED_ORIGINS` lists only production frontend origins; `localhost` origins are removed.
- [ ] All production traffic is served over HTTPS; HTTP-only connections are redirected at the load balancer.
- [ ] CORS preflight (`OPTIONS`) requests for all endpoints return the correct `Access-Control-Allow-Origin` header.

#### Audit Immutability

- [ ] `AuditEvent` Pydantic model has `frozen=True` — confirm attempts to mutate raise `ValidationError`.
- [ ] Couchbase collection `audit.events` has no update/delete permissions for application service account credentials — the service account should have `insert` only.
- [ ] Audit trail can be fully reconstructed for a complete agent workflow by querying `GET /api/audit/{object_id}` and verifying agent + human steps appear in order.

#### RBAC Smoke Test

Run the following sequence to validate role enforcement end-to-end:

- [ ] `fraud_analyst` token can `POST /api/fraud/events` and `POST /api/fraud/alerts/{id}/approve`.
- [ ] `fraud_analyst` token is rejected (HTTP 403) on `POST /api/loans/applications/{id}/decision`.
- [ ] `underwriter` token can `POST /api/loans/applications` and `POST /api/loans/applications/{id}/decision`.
- [ ] `underwriter` token is rejected on `GET /api/cases` (requires `compliance_reviewer` or `admin`).
- [ ] `compliance_reviewer` token can `GET /api/cases`, `GET /api/audit/{id}`, `GET /api/metrics/agents`.
- [ ] `compliance_reviewer` token is rejected on any `POST` approval endpoint.
- [ ] `admin` token succeeds on all endpoints.
- [ ] Unauthenticated request returns HTTP 401 on any protected endpoint.

#### Observability

- [ ] `OTEL_EXPORTER_OTLP_ENDPOINT` is set and spans appear in the collector.
- [ ] `OTEL_SERVICE_NAME` is correct in all exported spans.
- [ ] Agent traces (`TRC-` prefixed documents) are visible in `banking-core.audit.events` after a test workflow.
- [ ] `GET /api/metrics/agents` returns non-zero counts after seed data and at least one test transaction.
