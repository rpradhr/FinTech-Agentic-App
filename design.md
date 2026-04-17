# Design Document — Multi-Agent Banking Operations Platform

> **Version:** 1.0 | **Date:** April 2026 | **Status:** Living document

---

## Table of Contents

1. [PRD Translation](#1-prd-translation)
2. [Core Workflows](#2-core-workflows)
3. [Design Decisions](#3-design-decisions)
4. [Tradeoffs](#4-tradeoffs)
5. [MVP Boundaries](#5-mvp-boundaries)
6. [Risk Mitigations](#6-risk-mitigations)

---

## 1. PRD Translation

### Goals

The platform consolidates five distinct banking operations concerns — fraud detection, customer sentiment, loan underwriting, branch performance monitoring, and personalized financial advisory — into a single, AI-augmented operations hub. The core product hypothesis is that specialist AI agents, coordinated by a central supervisor and governed by mandatory human review gates, can reduce analyst workload, improve decision consistency, and surface actionable intelligence faster than siloed tooling.

The system is explicitly **not** designed to operate autonomously. Every consequential action (blocking a transaction, approving or declining a loan, delivering financial advice) requires human authorization. The agents are reasoning and triage tools, not decision-makers.

### Personas

| Persona | Primary Concern | Platform Entry Point |
|---|---|---|
| **Fraud Analyst** | Rapidly triage high-volume transaction alerts; distinguish genuine fraud from false positives | Fraud alert queue; Case workspace |
| **Branch Manager** | Understand KPI deviations at their branch; receive AI-generated narrative insights | Branch dashboard; Insight feed |
| **Loan Underwriter** | Review AI-generated loan assessments; make final approve/decline decisions | Loan review queue; Application detail |
| **Financial Advisor** | Prepare personalized financial plans for client meetings; receive AI-drafted recommendations | Advisory workspace; Customer profile |
| **Customer Service Rep** | Understand why a customer is unhappy; decide whether to escalate | Interaction analysis feed; Case queue |
| **Compliance Officer** | Audit all agent decisions; confirm no autonomous actions were taken | Audit log; Trace viewer |

### Agent Roles

| Agent | Input | Primary Output | HITL Gate |
|---|---|---|---|
| **Fraud Detection Agent** (`fraud_agent`) | `Transaction` + customer history + device patterns | `FraudAlert` with risk score, evidence, and recommended action | Analyst must approve before any block action |
| **Customer Sentiment Agent** (`sentiment_agent`) | `Interaction` transcript (call, email, complaint) | `InteractionAnalysis` with sentiment label, churn risk, themes, escalation flag | Escalation requires human decision |
| **Loan Reviewer Agent** (`loan_agent`) | `LoanApplication` + credit signals + policy documents | `LoanReview` with recommendation, risk flags, and policy exception list | Underwriter makes final decision |
| **Branch Monitor Agent** (`branch_agent`) | `BranchKPI` data + flagged transactions + interaction trends | `BranchInsight` narrative + `BranchAlert` for anomalies | Branch manager reviews insights before acting |
| **Financial Advisory Agent** (`advisory_agent`) | `CustomerProfile` + household data + financial goals + product catalog | `AdviceDraft` with personalized recommendations | Advisor must approve and may edit before delivery |

### Key Workflows (summary)

- **Transaction Ingestion → Fraud Triage:** Transactions arrive via REST or Kafka; the Supervisor routes each to the Fraud Agent; HIGH/CRITICAL alerts open a Case and queue for analyst review.
- **Interaction Ingestion → Sentiment Analysis → Optional Escalation:** Customer interactions are analyzed for sentiment and churn risk; escalation-flagged results open COMPLAINT Cases.
- **Loan Submission → AI Review → Underwriter Decision:** Applications are assessed against policy documents via RAG; the review package is queued for an underwriter.
- **Branch Monitoring → Insight Generation:** Scheduled or threshold-triggered analysis produces narrative summaries and operational alerts for branch managers.
- **Advisor Workspace → Draft Generation → Delivery:** Opening a customer workspace triggers the Advisory Agent; the resulting draft is editable by the advisor before any client communication.

---

## 2. Core Workflows

### 2.1 Fraud Triage

```
1.  Transaction event arrives (POST /api/v1/fraud/transactions  OR  Kafka topic banking.transactions)
2.  API router validates payload → Pydantic Transaction model
3.  Supervisor.process_transaction(txn) is called
4.  Supervisor assigns a session_id and dispatches to FraudAgent.analyze_transaction()
5.  FraudAgent fetches:
      a. CustomerProfile (recent activity baseline)
      b. Last 50 transactions (velocity / geo analysis)
      c. Device transaction history (device mismatch detection)
      d. Prior FraudAlerts for the customer (pattern recurrence)
      e. RAG context: fraud policy documents via vector search
6.  FraudAgent issues LLM completion → structured JSON output
7.  FraudAlert is created with status = PENDING_ANALYST_REVIEW
       ← ALL agent actions stop here ←
       [HITL GATE: analyst must review before any block/escalation]
8.  If risk_level in {HIGH, CRITICAL}:
      Supervisor._open_case() creates a Case (type=FRAUD, priority=HIGH|CRITICAL)
9.  FraudAlert + Case are persisted; alert appears in analyst queue
10. Analyst reviews alert in UI:
      → CONFIRM → FraudAlert.status = CONFIRMED_FRAUD + AuditEvent(FRAUD_ALERT_APPROVED)
      → CLEAR    → FraudAlert.status = CLEARED         + AuditEvent(FRAUD_ALERT_DECLINED)
      → ESCALATE → FraudAlert.status = ESCALATED       + AuditEvent(FRAUD_ALERT_ESCALATED)
11. Each analyst action emits an immutable AuditEvent
```

**HITL Gate:** Between steps 7 and 10. The agent produces a recommendation and an explanation; it never instructs the system to block a card or freeze an account. That instruction can only come from a human action on the review UI.

---

### 2.2 Loan Review

```
1.  Application submitted (POST /api/v1/loans/applications)
2.  Supervisor.process_loan_application(application) is called
3.  Supervisor dispatches to LoanAgent.review_application()
4.  LoanAgent fetches:
      a. CustomerProfile + credit signals
      b. Existing FraudAlerts for the customer (fraud cross-check)
      c. RAG context: lending policy documents, rate tables, exception criteria
5.  LoanAgent issues LLM completion → structured JSON review output
6.  LoanReview created (status = PENDING_UNDERWRITER_DECISION)
7.  Any policy exceptions detected → LoanException records created
       ← ALL agent actions stop here ←
       [HITL GATE: underwriter must make the final decision]
8.  Supervisor._open_case() creates a LOAN_REVIEW Case
9.  Underwriter reviews in UI:
      → APPROVE  → LoanReview decision set + AuditEvent(LOAN_DECISION_APPROVED)
      → DECLINE  → LoanReview decision set + AuditEvent(LOAN_DECISION_DECLINED)
      → REQUEST_EXCEPTION → LoanException escalated for policy committee
10. Application status updated to match underwriter decision
```

**HITL Gate:** Between steps 6 and 9. The agent provides a recommendation with cited evidence and policy references; the underwriter makes the binding credit decision.

---

### 2.3 Branch Monitoring

```
1.  Trigger: scheduled job OR KPI anomaly threshold breach
    (POST /api/v1/branches/{branch_id}/analyze)
2.  Supervisor.analyze_branch(branch_id) dispatches to BranchAgent.analyze_branch()
3.  BranchAgent fetches:
      a. BranchKPI records (last 30 days by default)
      b. Flagged transactions for the branch (fraud concentration)
      c. InteractionAnalyses for branch-linked customers (sentiment trend)
4.  BranchAgent issues LLM completion → narrative insight + alert list
5.  BranchInsight and BranchAlert records persisted
       ← Agent produces analysis only; no operational directive issued ←
       [HITL GATE: branch manager reviews insight before taking action]
6.  Branch manager reviews dashboard:
      → Acknowledges alerts → AuditEvent(BRANCH_ALERT_REVIEWED)
      → Escalates alert → Case opened (type=BRANCH)
```

**HITL Gate:** Between steps 5 and 6. Branch insights are advisory — no staffing, product, or operational change is made by the agent.

---

### 2.4 Advisor Assist (Financial Advisory)

```
1.  Advisor opens customer workspace (POST /api/v1/advisory/customers/{id}/advice)
2.  Supervisor.generate_advice(customer_id, advisor_id) dispatches to AdvisoryAgent
3.  AdvisoryAgent fetches:
      a. CustomerProfile + household members
      b. Open Cases for the customer (fraud / loan context awareness)
      c. Recent loan applications and their status
      d. Fraud flags (avoid recommending products to compromised accounts)
      e. RAG context: product catalog, suitability rules, regulatory guidance
4.  AdvisoryAgent issues LLM completion → personalized advice draft
5.  AdviceDraft created (status = PENDING_ADVISOR_REVIEW)
       ← ALL content stops here — nothing is sent to the customer ←
       [HITL GATE: advisor must review, optionally edit, then approve]
6.  Advisor reviews draft in UI:
      → APPROVE         → AdviceDraft.status = APPROVED + AuditEvent(ADVICE_DRAFT_APPROVED)
      → EDIT & SAVE     → advisor_edits stored   + AuditEvent(ADVICE_DRAFT_EDITED_AND_SAVED)
      → DECLINE         → draft discarded         + AuditEvent(RECOMMENDATION_OVERRIDDEN)
7.  Only after advisor approval can content be transmitted to the customer
```

**HITL Gate:** Between steps 5 and 6. This gate is a regulatory requirement — automated investment and financial advice delivery without human supervision violates suitability obligations.

---

### 2.5 Complaint / Sentiment Analysis

```
1.  Interaction received (POST /api/v1/interactions/)
    (call transcript, email thread, or chat log)
2.  Supervisor.process_interaction(interaction) dispatches to SentimentAgent
3.  SentimentAgent fetches:
      a. Customer interaction history (last 10 interactions)
      b. CustomerProfile (account standing, segment)
      c. RAG context: escalation playbooks, product complaint handling guides
4.  SentimentAgent issues LLM completion → InteractionAnalysis
      Fields: sentiment label, churn_risk (0-1), themes, escalation_recommended
5.  InteractionAnalysis persisted; CustomerProfile sentiment updated
       ← Analysis output only; no customer contact initiated ←
       [HITL GATE: service rep or supervisor decides on escalation]
6.  If analysis.escalation_recommended:
      Supervisor._open_case() opens a COMPLAINT Case (priority based on churn_risk)
7.  Service rep reviews Case:
      → Escalate to retention team → Case reassigned + AuditEvent
      → Resolve               → Case closed        + AuditEvent
```

**HITL Gate:** Between steps 5 and 7. The agent flags customers at churn risk and recommends escalation; the human representative decides whether and how to act.

---

## 3. Design Decisions

### 3.1 Supervisor-Orchestrated, Specialist-Agent Model

**Decision:** A single `Supervisor` class routes all domain events to one of five specialist agents. Agents do not communicate with each other directly; all cross-agent context assembly happens in the Supervisor or within each agent's context-gathering phase.

**Rationale:**

- **Auditability.** Every event passes through a single, observable chokepoint. The Supervisor is the natural place to enforce HITL rules — if the Supervisor never issues autonomous action commands, no agent can bypass the guardrails regardless of its LLM output.
- **Specialization beats generalism in regulated domains.** A single general agent with a wide prompt struggles to maintain depth across fraud patterns, credit policy, and suitability rules simultaneously. Specialist agents carry smaller, domain-focused system prompts that can be versioned, reviewed, and tested independently.
- **Independent deployability.** Each agent class is self-contained. A change to loan review prompts or logic requires no changes to the fraud or sentiment agents, reducing regression surface area.
- **Testability.** Agents can be unit-tested with mock LLM responses and stub repositories without bringing up the full orchestration graph.

**Alternative considered:** A multi-turn conversational graph (LangGraph / AutoGen style) where agents pass messages to each other. Rejected because the additional state management complexity and non-deterministic conversation length make compliance auditing significantly harder.

---

### 3.2 Couchbase Capella as Shared Context Layer

**Decision:** All agent-produced data (alerts, reviews, analyses, traces) is written to Couchbase Capella and read back by other agents that need cross-domain context. For example, the Advisory Agent reads FraudAlerts before generating recommendations to avoid advising customers with compromised accounts.

**Rationale:**

- **Schema flexibility.** Couchbase's document model accommodates the varied shapes of domain objects (a FraudAlert has different fields than a LoanReview) without the overhead of a migration-heavy relational schema.
- **Co-located vector search.** Capella's native vector search means retrieval-augmented generation (RAG) queries and document retrieval use the same cluster, connection pool, and authentication path. There is no separate vector database to operate or synchronize.
- **Sub-millisecond key-value access.** Agent context-gathering fetches (customer profile, recent transactions, prior alerts) are single-document lookups by primary key — a pattern Couchbase optimizes well.
- **Agent Tracer alignment.** Capella AI Services' Agent Tracer expects trace data to be written to a Couchbase collection, making native storage the lowest-friction integration path.

---

### 3.3 Repository Abstraction (interfaces.py)

**Decision:** All persistence access goes through abstract base classes defined in `interfaces.py`. The application and domain layers import only from `interfaces` — never from `couchbase/` or `memory/` directly.

**Rationale:**

- **Testability.** Tests run against `InMemoryStore` with zero network overhead. The in-memory adapters implement the same ABCs, so tests exercise real application logic.
- **Portability.** Swapping to a different database backend (Postgres, DynamoDB) requires only writing new adapter classes. No application or domain code changes.
- **Enforced boundaries.** Python's `ABC` with `@abstractmethod` makes the contract explicit and causes an immediate `TypeError` at instantiation time if an adapter forgets to implement a method.
- **Container wiring.** `Container` receives typed repository references (`CustomerRepository`, `FraudRepository`, etc.). From the application layer's perspective, these are always the interface types — the concrete adapter is resolved once at startup and never re-inspected.

---

### 3.4 In-Memory Adapter for Testing and Development

**Decision:** `InMemoryStore` (a single shared dictionary of collections) backs all `InMemory*Repository` classes. The `Container` automatically selects this backend when `APP_ENV=test` or when no Couchbase connection string is configured.

**Rationale:**

- Tests run in-process with no external dependencies, making CI fast and hermetic.
- Developers can run the full application stack without provisioning a Couchbase cluster, lowering the onboarding barrier.
- The in-memory adapter is realistic enough to validate application logic — it enforces the same method signatures and return types as the Couchbase adapter.

**Limitation acknowledged:** The in-memory adapter does not replicate Couchbase's SQL++ query semantics, index behavior, or eventual consistency model. Integration tests that validate query correctness must run against a real Couchbase cluster.

---

### 3.5 JSON Outputs from Agents

**Decision:** Each agent's system prompt instructs the LLM to return a strict JSON object. The agent parses the JSON and maps it to a Pydantic domain model (e.g., `FraudAlert`). The raw LLM string is never stored or acted upon directly.

**Rationale:**

- **Type safety.** Pydantic validation at the parse boundary means that if the LLM hallucinated an invalid `risk_level` string or a `risk_score` outside `[0.0, 1.0]`, the error surfaces immediately with a clear exception rather than propagating silently.
- **Auditability.** Structured JSON is straightforward to log, diff across model versions, and include in compliance reports.
- **No function-calling dependency.** Structured JSON prompting works across any LLM provider that can follow instructions, not just providers with first-class tool/function-calling APIs. This preserves the option to swap the model service.
- **Explicit schema.** The JSON schema in the system prompt doubles as documentation for what the agent is expected to reason about. Prompt engineers and reviewers can understand the agent's contract without reading code.

---

## 4. Tradeoffs

### 4.1 Capella-First vs. Multi-Cloud Portability

| | Capella-First (current) | Multi-Cloud Portable |
|---|---|---|
| **Operational cost** | Low — single cluster, single vendor, integrated vector search | Higher — separate vector DB, additional synchronization |
| **Feature integration** | Native Agent Tracer, AI Functions, Model Service | Manual integration for each provider's AI services |
| **Vendor lock-in risk** | Moderate — Couchbase query language (SQL++) and SDK are non-standard | Low — standard SQL, commodity S3, open vector DBs |
| **Migration cost if needed** | Only adapter classes change; domain/application untouched | Same; repository abstraction pays off here |

**Current stance:** Capella-first, with the repository abstraction preserving the option to migrate. The abstraction layer is the hedge against lock-in, not a reason to avoid the productivity benefits of Capella AI Services.

---

### 4.2 LLM JSON Output vs. Structured Tool Calling

| | JSON Prompting (current) | Tool / Function Calling |
|---|---|---|
| **Provider compatibility** | Works with any instruction-following model | Requires provider-specific tool-calling API |
| **Output reliability** | Occasional JSON parse failures (mitigated by retry + fallback) | Stronger structural guarantee from the provider |
| **Schema evolution** | Update system prompt; redeploy | Update tool schema; may require SDK changes |
| **Debugging** | LLM output visible in trace logs | Tool call arguments in trace logs |
| **Latency** | Single completion call | Potentially multi-turn if the model calls tools iteratively |

**Current stance:** JSON prompting is chosen for provider flexibility and simplicity. A Pydantic parse failure triggers a structured fallback (conservative defaults + explicit error log). If a provider with reliable structured output (OpenAI `response_format`, Anthropic tool use) is standardized, the agent `_complete` calls can be migrated without changing domain logic.

---

### 4.3 Real-Time vs. Batch for Branch Analytics

| | Real-Time (current default) | Batch (scheduled) |
|---|---|---|
| **Latency** | Insight available within seconds of trigger | Insight available on schedule (e.g., nightly) |
| **Compute cost** | LLM call per trigger; potentially frequent if thresholds are sensitive | Amortized: one LLM call per branch per cycle |
| **Staleness** | Low — analysis reflects current state | Moderate — up to one cycle stale |
| **Operational complexity** | Requires robust threshold logic to avoid over-triggering | Requires scheduler (Celery, APScheduler, or Kafka consumer) |

**Current stance:** Real-time on-demand (POST endpoint + threshold trigger) for MVP. Scheduled batch mode is supported via the same `Supervisor.analyze_branch()` entry point and is enabled with `eventing_enabled=true` in configuration.

---

## 5. MVP Boundaries

### In Scope (MVP)

- **Fraud Detection:** Transaction scoring, alert creation, analyst review queue, ring cluster detection, Case management.
- **Customer Sentiment:** Interaction analysis, churn risk scoring, escalation recommendation, COMPLAINT Case creation.
- **Loan Review:** Application assessment, policy RAG, exception detection, underwriter decision workflow, full audit trail.
- **Branch Monitoring:** KPI ingestion, narrative insight generation, alert management, branch dashboard.
- **Financial Advisory:** Personalized draft generation, advisor edit + approval workflow, household-aware context.
- **Case Management:** Unified Case workspace across all agent types with status, priority, and timeline.
- **Audit Log:** Immutable append-only audit trail for all agent and human actions.
- **Agent Tracing:** Full per-session step tracing (prompt tokens, latency, model ID) via `AgentTrace` model.
- **Auth:** JWT-based route protection with role claims; OIDC integration path configured.
- **Persistence:** Couchbase Capella (production) and in-memory (test/dev) adapters.
- **API:** REST endpoints for all five domains plus cases, auth, and admin routes.
- **Frontend:** React + TypeScript dashboard for all analyst/manager/advisor workflows.

### Out of Scope (Post-MVP)

- **Autonomous action execution:** The platform explicitly will not act on agent recommendations without human approval in any scope.
- **Real-time transaction streaming UI:** Kafka consumer exists; live dashboard push via WebSocket is post-MVP.
- **Multi-tenant isolation:** Single-tenant deployment assumed for MVP; tenant-scoped Couchbase scopes are a post-MVP extension.
- **Model fine-tuning pipeline:** All agents use base models via Capella AI Services; custom fine-tuned models are post-MVP.
- **Mobile application:** Web-only for MVP.
- **Automated regulatory reporting:** Audit log data export exists; automated SAR/CTR filing integration is post-MVP.
- **Peer-to-peer fraud graph visualization:** `FraudRingCluster` model exists; interactive network graph UI is post-MVP.
- **A/B testing framework for agent prompts:** Manual prompt versioning only for MVP.

---

## 6. Risk Mitigations

### 6.1 False Positives in Fraud Detection

**Risk:** High false positive rates cause analyst alert fatigue and erode trust in the system.

**Mitigations:**
- `FraudRiskLevel` thresholds are derived from continuous score ranges, not binary flags. Only HIGH (≥ 0.70) and CRITICAL (≥ 0.90) alerts automatically open Cases; MEDIUM alerts are surfaced in a secondary queue.
- The `RecommendedAction` enum includes `MONITOR` and `SOFT_BLOCK` as gradations below `HARD_BLOCK`, giving analysts nuanced options.
- Prior alert patterns are included in agent context so the LLM can recognize recurring false-positive profiles.
- Analyst decisions (CONFIRM / CLEAR) feed back into the audit log, enabling future training data collection for threshold calibration.

### 6.2 Retrieval Quality (RAG)

**Risk:** Low-quality vector search results cause agents to cite outdated or irrelevant policy documents, degrading recommendation quality.

**Mitigations:**
- `CapellaRetrievalService` uses `VECTOR_DISTANCE` with a configurable `top_k` and returns source metadata with every chunk. Agents include the source label in context so the LLM can weight recency and relevance.
- Retrieved context is logged in the `AgentTrace.input_data` field, making it possible to audit which documents influenced a given decision.
- The `retrieval_chunks` collection is versioned by document ingestion pipeline; stale chunks are soft-deleted before re-ingestion.
- Retrieval results are capped at `top_k=3` by default to prevent context window dilution.

### 6.3 Model Drift

**Risk:** LLM provider model updates change output behavior, causing agent JSON schemas to fail to parse or recommendations to shift in distribution.

**Mitigations:**
- Each `AgentTrace` records `model_id` exactly as returned by the provider. Drift can be detected by comparing output distributions across model versions in the trace store.
- Agent system prompts pin behavioral constraints (output schema, forbidden fields) that are stable across model versions.
- The stub AI backend allows replay testing of historical inputs against new model versions before cutover.
- Pydantic parse failures are caught, logged with full context, and surfaced as structured errors rather than silent degradations.

### 6.4 Data Leakage Between Customers

**Risk:** Agent context assembly inadvertently includes one customer's data in another customer's analysis.

**Mitigations:**
- All repository fetch methods are scoped to a `customer_id` or a domain-specific primary key (e.g., `branch_id`). There are no "fetch all" queries in production paths that could return cross-customer data.
- `CustomerProfile`, `FraudAlert`, `LoanApplication`, and `AdviceDraft` all carry `customer_id` as a mandatory field. The application layer passes this as a parameter to every fetch; it is never inferred from context.
- JWT role claims include customer context for customer-facing API paths; advisor and analyst routes require explicit role claims validated before data is fetched.
- The Couchbase Capella `customers` scope is isolated from the `agents` scope, allowing fine-grained RBAC at the Capella data-access layer.
- Audit events carry `customer_id` on every record, enabling post-hoc detection of any cross-customer data access anomalies.
