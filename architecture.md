# Architecture Reference — Multi-Agent Banking Operations Platform

> **Version:** 1.0 | **Date:** April 2026 | **Status:** Living document

---

## Table of Contents

1. [Component Architecture](#1-component-architecture)
2. [Agent Orchestration](#2-agent-orchestration)
3. [Service Boundaries](#3-service-boundaries)
4. [Storage Abstraction](#4-storage-abstraction)
5. [Couchbase / Capella Adapter Design](#5-couchbase--capella-adapter-design)
6. [Portability Strategy](#6-portability-strategy)
7. [Scalability Notes](#7-scalability-notes)
8. [Security Notes](#8-security-notes)
9. [Observability Notes](#9-observability-notes)

---

## 1. Component Architecture

### Layer Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT TIER                                     │
│   React + TypeScript SPA (Vite)                                              │
│   Roles: Fraud Analyst · Underwriter · Branch Manager · Advisor · Rep        │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │  HTTPS / REST
┌─────────────────────────────▼────────────────────────────────────────────────┐
│                              API LAYER  (FastAPI)                            │
│  ┌──────────┐ ┌───────────┐ ┌──────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ /fraud   │ │ /loans    │ │/int- │ │/branches │ │/advisory │ │/cases  │  │
│  │          │ │           │ │eract │ │          │ │          │ │        │  │
│  └──────────┘ └───────────┘ └──────┘ └──────────┘ └──────────┘ └────────┘  │
│  JWT auth middleware · Pydantic request/response schemas · OpenAPI docs      │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │  async function calls
┌─────────────────────────────▼────────────────────────────────────────────────┐
│                        APPLICATION LAYER                                     │
│                                                                              │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │                    Supervisor (orchestrator.py)                     │    │
│   │  process_transaction() · process_interaction() · process_loan()    │    │
│   │  analyze_branch()      · generate_advice()     · _open_case()      │    │
│   └──────┬──────────┬──────────┬──────────┬──────────┬────────────────┘    │
│          │          │          │          │          │                       │
│   ┌──────▼──┐ ┌─────▼───┐ ┌───▼────┐ ┌──▼─────┐ ┌──▼──────┐              │
│   │ Fraud   │ │Sentiment│ │  Loan  │ │ Branch │ │Advisory │              │
│   │  Agent  │ │  Agent  │ │  Agent │ │  Agent │ │  Agent  │              │
│   └──────┬──┘ └─────┬───┘ └───┬────┘ └──┬─────┘ └──┬──────┘              │
│          └──────────┴──────────┴──────────┴──────────┘                      │
│                               BaseAgent                                      │
│           _complete() · _emit_audit() · _retrieve_context()                  │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │  repository interfaces (ABCs)
┌─────────────────────────────▼────────────────────────────────────────────────┐
│                       INFRASTRUCTURE LAYER                                   │
│                                                                              │
│  ┌──────────────────────────────────┐  ┌───────────────────────────────┐    │
│  │        Persistence               │  │        AI Services            │    │
│  │                                  │  │                               │    │
│  │  interfaces.py (ABCs)            │  │  LLMService (ABC)             │    │
│  │     ├── CouchbaseClient          │  │  EmbeddingService (ABC)       │    │
│  │     │   └── repositories.py      │  │  RetrievalService (ABC)       │    │
│  │     └── InMemoryStore            │  │     ├── CapellaLLMService     │    │
│  │         └── repositories.py      │  │     ├── CapellaEmbedding      │    │
│  │                                  │  │     ├── CapellaRetrieval      │    │
│  │  Container (container.py)        │  │     └── Stub*Service          │    │
│  └──────────────────────────────────┘  └───────────────────────────────┘    │
│                                                                              │
│  Kafka consumer (eventing_enabled=true) — optional event-driven ingestion   │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────────────────┐
│                         DOMAIN LAYER                                         │
│  Pure Python / Pydantic v2 models — zero infrastructure imports              │
│                                                                              │
│  Customer · Transaction · FraudAlert · FraudRingCluster                      │
│  LoanApplication · LoanReview · LoanException                                │
│  Interaction · InteractionAnalysis · CustomerSignal                          │
│  BranchKPI · BranchAlert · BranchInsight                                     │
│  AdviceDraft · Case · AuditEvent · AgentTrace · Household                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Layer Descriptions

**Client Tier:** A React + TypeScript single-page application served from a separate origin (`localhost:5173` in development). It communicates exclusively through the REST API. Role-specific views are rendered based on JWT claims decoded client-side; route-level authorization is always enforced server-side.

**API Layer:** FastAPI routers grouped by domain (`/fraud`, `/loans`, `/interactions`, `/branches`, `/advisory`, `/cases`). Each router depends on the `Container` singleton via `Depends(get_container)`. Request and response shapes are defined as Pydantic schemas in `api/schemas.py` — distinct from domain models to allow independent API versioning. JWT middleware validates tokens on every non-public endpoint.

**Application Layer:** Contains all business logic. The `Supervisor` is the single entry point for all event processing. Specialist agents perform reasoning using the LLM and repository services injected at construction time. No application class imports from `infrastructure.persistence.couchbase` or `infrastructure.persistence.memory` directly.

**Infrastructure Layer:** Provides concrete implementations of all abstract interfaces. The `Container` class resolves the correct adapter based on `Settings.database_backend` at startup. AI services have a parallel interface/implementation structure: `CapellaLLMService` for production, `StubLLMService` for test and development.

**Domain Layer:** Pydantic v2 `BaseModel` classes with no infrastructure dependencies. These are the canonical data shapes for the entire system. Any layer can import domain models; no layer below the application layer imports from above it.

---

## 2. Agent Orchestration

### The Supervisor Class

`app/application/orchestrator.py` defines the `Supervisor` class, which is the sole entry point for all agent-mediated operations. Route handlers never call agent methods directly.

```
Supervisor
├── process_transaction(txn: Transaction)         → Optional[FraudAlert]
├── process_interaction(interaction: Interaction) → None
├── process_loan_application(app: LoanApplication)→ LoanReview
├── analyze_branch(branch_id: str)                → BranchInsight
├── generate_advice(customer_id, advisor_id)      → AdviceDraft
└── _open_case(type, title, customer_id, ...)     → Case
```

The Supervisor is constructed once per application startup by `build_supervisor(container)`, which injects all agent instances and shared repository references (`case_repo`, `audit_repo`, `trace_repo`).

### Event Routing

Each public method on `Supervisor` maps to exactly one specialist agent entry point:

| Incoming Event | Supervisor Method | Routed To |
|---|---|---|
| Transaction submitted | `process_transaction` | `FraudAgent.analyze_transaction` |
| Interaction recorded | `process_interaction` | `SentimentAgent.analyze_interaction` |
| Loan application submitted | `process_loan_application` | `LoanAgent.review_application` |
| Branch analysis requested | `analyze_branch` | `BranchAgent.analyze_branch` |
| Advisor workspace opened | `generate_advice` | `AdvisoryAgent.generate_advice_draft` |

### Session Identity

Every Supervisor method call generates a `session_id` using `new_session_id()` (UUID4). This ID is threaded through to every `AgentTrace` produced during that call, enabling full reconstruction of a reasoning session from the trace store.

### Case Opening

The Supervisor's `_open_case()` method is the only place a `Case` is created programmatically. It is called by the Supervisor after an agent produces a result that meets escalation criteria:

- `FraudAgent` result with `risk_level in {HIGH, CRITICAL}` → `CaseType.FRAUD`
- `SentimentAgent` result with `escalation_recommended=True` → `CaseType.COMPLAINT`
- `LoanAgent` result (all applications) → `CaseType.LOAN_REVIEW`

The Case links to the originating entity (alert ID, review ID, analysis ID) via `linked_entity_ids` and `linked_entity_types`.

### Preventing Autonomous Action

The architecture enforces the HITL constraint at three levels:

1. **Agent design:** Agent methods return domain models (e.g., `FraudAlert`) with status fields initialized to a `PENDING_*` state. No agent method calls any service that changes external state (blocks a card, sends an email, updates an application status).
2. **Supervisor design:** The Supervisor never issues commands beyond creating records (Cases, Alerts, Reviews) and reading context. Commands like `update_alert_status(decision=CONFIRMED_FRAUD)` are only callable from API route handlers, which require an authenticated human user with the correct role.
3. **Audit enforcement:** Every state transition on a consequential object (`FraudAlert`, `LoanReview`, `AdviceDraft`) requires an `AuditEvent` with `actor_type=HUMAN` and a real `actor_id`. The `AuditRepository.append` interface is write-only — records cannot be updated or deleted.

---

## 3. Service Boundaries

### Per-Agent Ownership

Each specialist agent owns a specific repository and is the only application component that writes to it:

| Agent | Owned Repository | Write Operations |
|---|---|---|
| `FraudAgent` | `FraudRepository` | `save_alert`, `save_ring_cluster` |
| `SentimentAgent` | `InteractionRepository` | `save_interaction`, `save_analysis`; `CustomerRepository.update_sentiment` |
| `LoanAgent` | `LoanRepository` | `save_review`, `save_exception`; `LoanRepository.update_application_status` |
| `BranchAgent` | `BranchRepository` | `save_kpi`, `save_alert`, `save_insight` |
| `AdvisoryAgent` | `AdvisoryRepository` | `save_draft` |

Agents **read** from repositories they do not own for cross-domain context (e.g., `AdvisoryAgent` reads `FraudRepository` and `LoanRepository`). All reads are via the same abstract interfaces.

### Shared Services

All agents inherit `BaseAgent` and share three cross-cutting services injected at construction:

**Audit Service (`AuditRepository`):** Every agent emits `AuditEvent` records via `BaseAgent._emit_audit()`. This is the compliance record of what the agent received and what it produced. Events are immutable (`AuditEvent` has `frozen=True` in its Pydantic config).

**Trace Service (`TraceRepository`):** Every LLM completion call in `BaseAgent._complete()` appends an `AgentTrace` record capturing the model ID, token counts, latency, truncated input messages, and truncated output. This is the observability record for performance monitoring and prompt debugging.

**Retrieval Service (`RetrievalService`):** All agents call `BaseAgent._retrieve_context(query, collection, top_k)` to fetch RAG context before LLM completion. The retrieval service abstracts vector search — `CapellaRetrievalService` issues `VECTOR_DISTANCE` queries against Capella; `StubRetrievalService` returns empty results in tests.

---

## 4. Storage Abstraction

### Repository Interface Pattern

`backend/app/infrastructure/persistence/interfaces.py` defines ten abstract base classes:

```
CustomerRepository    — profiles, households, signals
TransactionRepository — ledger events, device history, merchant history
FraudRepository       — alerts, ring clusters, similar pattern lookup
LoanRepository        — applications, reviews, exceptions
InteractionRepository — transcripts, analyses
BranchRepository      — KPIs, alerts, insights, dashboard summary
CaseRepository        — case management
AdvisoryRepository    — advice drafts
AuditRepository       — immutable event append
TraceRepository       — agent trace append and session lookup
```

Every method in every ABC is `@abstractmethod` and uses Python's `async def` signature. Synchronous Couchbase SDK calls are wrapped in `asyncio.get_event_loop().run_in_executor()` inside the Couchbase adapter to avoid blocking the event loop.

The application and domain layers import only:

```python
from app.infrastructure.persistence.interfaces import FraudRepository
```

They never import:

```python
from app.infrastructure.persistence.couchbase.repositories import CouchbaseFraudRepository  # WRONG
from app.infrastructure.persistence.memory.repositories import InMemoryFraudRepository       # WRONG
```

### Container Wiring

`Container.__init__` reads `Settings.database_backend` and branches:

```python
if settings.database_backend == DatabaseBackend.COUCHBASE:
    self._init_couchbase()   # instantiates CouchbaseClient + all Couchbase* repos
else:
    self._init_memory()      # instantiates InMemoryStore + all InMemory* repos
```

After construction, all repository attributes are typed as the abstract interface (`self.fraud: FraudRepository`), not the concrete class. The rest of the application is unaware of which concrete class is behind the reference.

### Adding a New Adapter

To add a PostgreSQL adapter (for example):

1. Create `backend/app/infrastructure/persistence/postgres/` with `client.py` and `repositories.py`.
2. In `repositories.py`, write one class per ABC from `interfaces.py`, implementing all `@abstractmethod` methods.
3. In `container.py`, add `DatabaseBackend.POSTGRES` to the `DatabaseBackend` enum and add an `_init_postgres()` method that instantiates the client and all Postgres repository classes.
4. Add the corresponding `elif` branch in `Container.__init__`.

Zero changes are required in `orchestrator.py`, any agent class, any domain model, or any API route handler.

---

## 5. Couchbase / Capella Adapter Design

### Bucket / Scope / Collection Mapping

All data lives in the `banking-core` bucket. Collections are organized into domain-aligned scopes:

```
banking-core  (bucket)
├── customers      (scope)
│   ├── profiles          ← CustomerProfile documents
│   ├── households        ← Household documents
│   └── preferences       ← CustomerSignal documents
├── transactions   (scope)
│   ├── ledger_events     ← Transaction documents
│   └── devices           ← device metadata
├── loans          (scope)
│   ├── applications      ← LoanApplication documents
│   ├── reviews           ← LoanReview documents
│   └── policy_refs       ← LoanException documents
├── interactions   (scope)
│   ├── transcripts       ← Interaction documents
│   └── analysis          ← InteractionAnalysis documents
├── branches       (scope)
│   ├── kpis              ← BranchKPI documents
│   └── alerts            ← BranchAlert + BranchInsight documents
├── agents         (scope)
│   ├── recommendations   ← FraudAlert + AdviceDraft documents
│   ├── case_context      ← Case + FraudRingCluster documents
│   └── session_state     ← agent session metadata
└── audit          (scope)
    └── events            ← AuditEvent + AgentTrace documents
```

The logical-to-physical mapping is defined in `COLLECTION_MAP` in `client.py`. Application code uses logical names (e.g., `"fraud_alerts"`); the `CouchbaseClient.get_collection(logical_name)` method resolves to the correct `(scope, collection)` pair.

### Document Key Convention

Documents use domain-meaningful string keys:

```
customers/profiles          → customer_id  (e.g., "cust_01J...")
transactions/ledger_events  → txn_id
agents/recommendations      → alert_id  OR  draft_id
loans/applications          → application_id
audit/events                → event_id  (UUID4, no semantic prefix)
```

### SQL++ Queries

List queries (e.g., `list_pending_alerts`, `get_recent_kpis`) use SQL++ (N1QL) via the cluster's `query()` method, also wrapped in `_run_sync`:

```python
query = """
    SELECT META().id, r.*
    FROM `banking-core`.`loans`.`reviews` AS r
    WHERE r.underwriter_decision IS MISSING
    LIMIT $limit
"""
result = await _run_sync(self._client.cluster().query, query, QueryOptions(
    named_parameters={"limit": limit}
))
```

Indexes must be provisioned before deploying; the `scripts/` directory contains index DDL for each collection.

### Vector Search via VECTOR_DISTANCE

The `CapellaRetrievalService` issues vector search queries against a Capella Search index named `banking-vector-index` (configurable via `Settings.couchbase_vector_index`):

```python
query = f"""
    SELECT t.content, t.source, t.doc_type,
           VECTOR_DISTANCE(t.embedding, $query_vector) AS distance
    FROM `banking-core`.`retrieval`.`chunks` AS t
    ORDER BY distance ASC
    LIMIT {top_k}
"""
```

The embedding for the query string is produced by `CapellaEmbeddingService` before the SQL++ call. Result chunks are returned with their `source` field so the caller can attribute citations.

### `_run_sync` Pattern

The Couchbase Python SDK is synchronous. All SDK calls are dispatched to the default thread pool executor to prevent blocking the asyncio event loop:

```python
def _run_sync(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, lambda: fn(*args, **kwargs))
```

Every `_get`, `_upsert`, and query call in the Couchbase repositories awaits `_run_sync(...)`. This pattern is consistent across all repository methods and is the only mechanism by which synchronous SDK operations are made compatible with FastAPI's async request handling.

---

## 6. Portability Strategy

The repository abstraction was designed explicitly so that the persistence backend can be replaced without touching any code above the infrastructure layer.

### What Changes When Switching from Couchbase to PostgreSQL

| File / Module | Changes Required |
|---|---|
| `infrastructure/persistence/postgres/client.py` | **New file.** SQLAlchemy async engine + session factory. |
| `infrastructure/persistence/postgres/repositories.py` | **New file.** One class per ABC; SQL queries instead of Couchbase SDK calls. |
| `core/container.py` | **Minor addition.** Add `DatabaseBackend.POSTGRES` enum value and `_init_postgres()` method. |
| `core/config.py` | **Minor addition.** Add `postgres_dsn` setting field. |

### What Does Not Change

| Module | Reason |
|---|---|
| `domain/models/*` | Pure Pydantic models; no persistence concern |
| `application/agents/*` | Imports only from `interfaces.py` |
| `application/orchestrator.py` | Imports only from `interfaces.py` |
| `api/routers/*` | Depends on `Container` attributes typed as ABCs |
| `infrastructure/persistence/interfaces.py` | The contract is the same; a new adapter implements it |
| All tests | Tests use the in-memory adapter; they continue to pass unchanged |

The total blast radius of a database migration is two new files plus minor additions to two existing files.

---

## 7. Scalability Notes

### Horizontal Scaling of FastAPI Workers

FastAPI is a stateless ASGI application. Multiple worker instances can be deployed behind a load balancer (e.g., AWS ALB, Nginx) with no shared in-process state:

- All state is in Couchbase; workers share one cluster.
- The `Container` singleton is per-process. Each worker initializes its own `CouchbaseClient` connection pool on startup.
- JWT validation is stateless (signature verification from public key); no session store is required.
- Recommended deployment: Gunicorn with `uvicorn.workers.UvicornWorker`, scaled via Kubernetes HPA on CPU or request queue depth.

### Event-Driven Ingestion via Kafka

When `Settings.eventing_enabled=True`, the application attaches Kafka consumers for:

```
kafka_transaction_topic   = "banking.transactions"
kafka_interaction_topic   = "banking.interactions"
```

Consumer groups allow multiple workers to partition the topic load. Each consumed message is deserialized to a `Transaction` or `Interaction` domain model and passed to the appropriate `Supervisor` method — the same code path as the REST endpoint. No special handling is required in the Supervisor or agents.

This makes the ingestion path horizontally scalable independently of the API tier: ingest workers can be scaled based on Kafka consumer lag without affecting API response latency.

### Read vs. Write Patterns

| Pattern | Characteristic | Optimization |
|---|---|---|
| Alert queue fetch (`list_pending_alerts`) | Frequent reads, low write rate | Secondary index on `status` + `created_at` |
| Transaction history (`get_recent_by_customer`) | High read volume, append-only writes | Index on `customer_id` + `created_at DESC` |
| Audit log (`append`) | Write-heavy, rarely read in real-time | Separate `audit` scope; no read indexes needed for hot path |
| Agent traces (`append_trace`) | Write-heavy during active sessions | Batch write or async fire-and-forget acceptable |
| Vector search (RAG) | Read-only at query time; write at ingest time | Separate ingestion pipeline; Capella Search index rebuilt on change |
| Branch dashboard (`list_branches_dashboard`) | Periodic reads, moderate data volume | Materialized KPI view refreshed on each `save_kpi` call |

---

## 8. Security Notes

### RBAC via JWT Role Claims

Every protected API endpoint validates a JWT bearer token. Role claims in the token determine which operations are permitted:

| Role Claim | Permitted Operations |
|---|---|
| `fraud_analyst` | Read fraud alerts, update alert status (confirm/clear/escalate) |
| `underwriter` | Read loan reviews, submit underwriter decisions |
| `branch_manager` | Read branch KPIs, insights, and alerts; acknowledge alerts |
| `financial_advisor` | Read and approve/edit advice drafts; access customer profiles |
| `service_rep` | Read interaction analyses, manage complaint cases |
| `compliance_officer` | Read-only access to audit log, traces, and all case data |
| `admin` | All operations; user management |

Role enforcement is applied in route handlers via a `require_role(...)` dependency injected with `Depends`. The Supervisor and agents do not perform their own role checks — access control is a boundary concern at the API layer.

### PII Scoping

Customer PII is contained within the `customers` Couchbase scope. Application queries that do not require full profile data (e.g., branch analytics) use aggregated fields only and do not fetch `profiles` documents. The `customers` scope can be granted read access exclusively to roles that require it (advisor, service rep) via Capella's data-plane RBAC.

`AdviceDraft` and `InteractionAnalysis` store summaries, not raw transcripts. Raw transcripts (`Interaction.transcript`) are stored in `interactions/transcripts` under a separate collection access policy.

### Audit Immutability

`AuditEvent` is defined with `frozen=True` in its Pydantic `Config`, making instances immutable in Python. The `AuditRepository.append` interface exposes only write and read methods — there is no `update` or `delete` method. In Couchbase, the `audit/events` collection can be protected with a bucket policy that denies `DELETE` and `REPLACE` mutations from application credentials.

### OIDC Production Path

`Settings` includes `oidc_issuer_url`, `oidc_client_id`, and `oidc_client_secret`. In production, JWT tokens are issued by the configured OIDC provider (Okta, Azure AD, etc.) and validated against the provider's JWKS endpoint. The `jwt_algorithm` setting switches from `HS256` (symmetric, dev only) to `RS256` (asymmetric, production). The `auth.py` middleware is designed to support both modes without code changes — only configuration differs.

---

## 9. Observability Notes

### OpenTelemetry Integration Point

`Settings.otel_exporter_otlp_endpoint` and `Settings.otel_service_name` are defined for OpenTelemetry configuration. The application startup sequence in `main.py` is the correct place to initialize the OTel SDK:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider(resource=Resource({"service.name": settings.otel_service_name}))
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
)
trace.set_tracer_provider(provider)
```

FastAPI's ASGI instrumentation (`opentelemetry-instrumentation-fastapi`) propagates trace context automatically through all request handlers. Custom spans can be added inside agent methods to correlate LLM call latency with HTTP request traces.

### Agent Tracer Alignment

Capella AI Services provides an Agent Tracer that expects trace data in a specific schema written to a Couchbase collection. The `AgentTrace` domain model is designed to align with this schema:

```python
class AgentTrace(BaseModel):
    trace_id: str          # UUID4 — unique per step
    session_id: str        # UUID4 — groups steps within one agent invocation
    agent_name: str        # e.g., "fraud_agent", "loan_agent"
    step_type: str         # "llm_call" | "tool_call" | "retrieval" | "handoff"
    step_index: int        # sequential within session
    input_data: dict       # truncated prompt context
    output_data: dict      # truncated LLM output
    model_id: str          # model identifier as returned by provider
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    ts: datetime
```

`BaseAgent._complete()` writes one `AgentTrace` per LLM call. If `BaseAgent._retrieve_context()` is extended to also emit traces (step_type `"retrieval"`), the full reasoning graph for each session becomes queryable.

### Structured Logging

All modules use `logging.getLogger(__name__)` with standard Python logging. The `core/logging.py` module configures JSON-structured output in non-development environments, compatible with log aggregation systems (Datadog, Splunk, CloudWatch). Key fields included in every structured log record:

- `trace_id` / `span_id` (from OTel context propagation)
- `session_id` (threaded through Supervisor methods)
- `agent_name` (set on every agent logger)
- `customer_id` (where present, for correlation without full PII)

### AgentTrace as a Debugging Tool

Because every LLM call writes an `AgentTrace`, developers and prompt engineers can reconstruct an exact agent session by querying:

```sql
SELECT *
FROM `banking-core`.`audit`.`events` AS t
WHERE t.session_id = $session_id
  AND t.agent_name = "fraud_agent"
ORDER BY t.step_index ASC
```

This surfaces the exact messages sent to the LLM (truncated at 200 characters per message in `input_data`) and the raw response (truncated at 500 characters in `output_data`), along with model identity, token counts, and latency — sufficient to debug prompt regressions and token budget overruns without storing full raw prompts in production.
