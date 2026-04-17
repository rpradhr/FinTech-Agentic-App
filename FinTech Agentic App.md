## **1\. PRD**

### **Overview**

This PRD defines a production-oriented, multi-agent banking application built on **Couchbase Capella Operational** as the primary operational datastore and **Capella AI Services** for AI-related capabilities. It is based on the application brief you attached, with the first requirement being a complete PRD.

**Working assumptions used to resolve underspecified items:**

* Institution type: **mid-size retail bank**  
* Document style: **internal product-spec**, not board memo  
* Initial audience: **primarily internal employee workflows**, with a controlled customer/advisor experience for financial guidance  
* Reference stack: **React \+ FastAPI \+ Python orchestration**  
* Delivery posture: **MVP-first, with a credible path to enterprise production**

Capella AI Services currently exposes documented building blocks including **Model Service**, **AI Services Workflows**, **Agent Catalog**, **Agent Tracer**, **AI Functions**, and **AI Services APIs**. Capella vector search is supported on operational clusters, and Agent Catalog is documented as working with Capella as a profile, transactional, or vector store. ([Couchbase Docs](https://docs.couchbase.com/ai/get-started/intro.html))

### **Problem Statement**

Financial institutions have fragmented intelligence across transactions, customer interactions, loan workflows, branch operations, and advisory journeys. Teams often use separate dashboards and manual review queues, which creates:

* slow fraud triage  
* weak cross-signal detection  
* inconsistent loan reviews  
* delayed branch performance interventions  
* generic rather than contextual financial advice

The product goal is to unify these workflows into an operational AI application that can **detect, summarize, prioritize, recommend, and escalate** while preserving human review for sensitive decisions.

### **Goals and Non-Goals**

**Goals**

1. Reduce analyst time-to-insight across fraud, sentiment, lending, branch ops, and advisory workflows.  
2. Use shared customer and operational context so agents do not operate in isolation.  
3. Keep the system explainable, auditable, and human-governed.  
4. Ship an MVP that is implementable using documented Capella capabilities.

**Non-Goals**

1. Fully autonomous fraud blocking or autonomous loan approval.  
2. Full core banking replacement.  
3. Unsupported claims around regulatory certification or compliance coverage.  
4. General-purpose consumer chatbot for all banking intents.

### **Personas**

| Persona | Primary Need | Key Pain |
| ----- | ----- | ----- |
| Fraud Analyst | Investigate suspicious activity quickly | Too many false positives and disconnected evidence |
| Contact Center / CX Lead | Understand dissatisfaction and escalation risk | Feedback is trapped in transcripts and case notes |
| Loan Underwriter | Review applications faster and more consistently | Missing docs, inconsistent summaries, policy exceptions |
| Regional Operations Manager | Monitor branch performance | KPIs lack root-cause context |
| Financial Advisor / Banker | Personalize guidance | Advice is generic and not grounded in current customer context |
| Compliance / Risk Reviewer | Audit decisions and interventions | Hard to reconstruct why a recommendation was made |

### **Jobs to Be Done**

* “When suspicious behavior emerges, help me see the risk, evidence, and next-best action before I escalate.”  
* “When customer dissatisfaction rises, tell me what is driving it and which relationships are at risk.”  
* “When a loan file arrives, summarize it, detect gaps, and propose a disposition for review.”  
* “When a branch underperforms, identify likely drivers instead of just showing KPI deltas.”  
* “When advising a customer, generate explainable recommendations grounded in profile, holdings, and goals.”

### **Key Use Cases**

1. Fraud ring detection across related accounts, cards, merchants, devices, and branches.  
2. Complaint clustering and churn-risk detection from calls, messages, and surveys.  
3. Loan file triage with missing-document detection and policy-exception surfacing.  
4. Branch anomaly detection across teller performance, wait times, complaints, staffing, and sales.  
5. Personalized savings, budgeting, product-fit, and follow-up recommendations.

### **Functional Requirements**

| ID | Requirement | Priority |
| ----- | ----- | ----- |
| FR-1 | Ingest transactions, customer profiles, loan applications, service interactions, and branch KPIs into Capella | P0 |
| FR-2 | Support five specialized agents with distinct roles and workbenches | P0 |
| FR-3 | Maintain shared customer/relationship context across agents | P0 |
| FR-4 | Provide explainable outputs with evidence, rationale, and confidence/risk scores | P0 |
| FR-5 | Require human approval for fraud actions, loan dispositions, and customer-facing financial recommendations | P0 |
| FR-6 | Store all actions, recommendations, and overrides in audit logs | P0 |
| FR-7 | Support semantic retrieval over interaction notes, policy docs, loan documents, and knowledge artifacts | P0 |
| FR-8 | Provide alert queues, dashboards, and case management views | P0 |
| FR-9 | Support inter-agent handoffs and shared signals | P1 |
| FR-10 | Capture traces for prompts, tool calls, handoffs, and outputs | P1 |
| FR-11 | Support feedback capture to evaluate agent usefulness and override rates | P1 |
| FR-12 | Provide customer-facing advisory nudges in a controlled channel | P2 |

### **Non-Functional Requirements**

| Domain | Requirement |
| ----- | ----- |
| Latency | P95 \< 2s for dashboard reads, \< 5s for standard agent summaries, \< 15s for complex case synthesis |
| Throughput | Sustain bursty transaction/event ingestion and concurrent analyst sessions |
| Resilience | Degrade gracefully: if AI inference fails, preserve operational workflow with deterministic fallback |
| Auditability | Every recommendation, action, prompt version, tool call, and human override must be reconstructible |
| Security | Role-based access, scoped data access, encryption in transit and at rest, tenant and environment isolation |
| Explainability | Outputs must include source facts, matched records, and model-generated rationale |
| Privacy | Sensitive fields masked where not needed; least-privilege retrieval |
| Observability | Full request tracing, agent traceability, queue depth, latency, model and workflow metrics |
| Data Freshness | Near-real-time for operational events; periodic aggregation for branch analytics |

### **User Flows**

1. **Fraud triage flow**  
   * Event arrives from transaction stream  
   * Fraud agent scores and explains  
   * Case is opened with linked evidence  
   * Analyst approves/declines recommended action  
   * Outcome feeds evaluation set  
2. **Loan review flow**  
   * Application submitted  
   * Loan agent summarizes application and documents  
   * Missing data and policy exceptions highlighted  
   * Underwriter reviews and decides next step  
3. **Branch ops flow**  
   * Daily/streaming KPIs updated  
   * Branch agent flags anomalies and likely drivers  
   * Manager reviews trend cards and actions  
4. **Advisor flow**  
   * Advisor opens customer workspace  
   * Advisory agent synthesizes profile, goals, holdings, and recent service sentiment  
   * Advisor approves or edits recommended outreach

### **Success Metrics**

* Fraud analyst review time reduced by 30%  
* False-positive workload reduced by 20% without material recall degradation  
* Loan file initial triage time reduced by 40%  
* Branch issue detection lead time improved by 25%  
* Advisor recommendation acceptance or edit-save rate \> 50%  
* Full audit reconstruction success rate: 100%  
* Human override rate tracked by agent and reason code

### **Risks and Dependencies**

**Risks**

* High false positives in fraud or branch anomaly detection  
* Weak explainability causing low trust  
* Retrieval quality degradation from poor chunking or stale knowledge  
* Model drift and policy changes  
* Sensitive data leakage across roles

**Dependencies**

* Clean event feeds from banking systems  
* Policy and product documents for retrieval corpus  
* Identity and RBAC integration  
* Human operations teams to review decisions  
* Capella AI Services environment, model deployments, and workflow configuration

### **MVP Definition**

**MVP includes**

* Fraud Detection Analyst  
* Customer Sentiment Analyzer  
* Loan Reviewer Agent  
* Shared case workspace  
* Branch dashboard lite  
* Advisor assist for internal users only  
* Audit logs, human approval, evaluation capture

**MVP excludes**

* Autonomous customer messaging  
* Full omnichannel chatbot  
* Deep forecasting for branch staffing  
* Complex portfolio optimization

### **Future Enhancements**

* Proactive branch staffing optimization  
* Relationship-level lifetime value actions  
* Cross-sell models integrated with advisory workflows  
* Multi-language sentiment and translation workflows  
* Advanced graph-based fraud ring analytics  
* Real-time event-driven nudges to customers

---

## **2\. Executive Summary**

This product is a **multi-agent banking operations application** that uses Capella as both the operational system of record and the memory/context layer for AI-assisted workflows. The design is intentionally pragmatic: structured operational data remains in Capella collections, document and interaction retrieval uses vector search plus AI Services Workflows, model inference is hosted through Capella Model Service, and agent prompts/tools/traces are managed through Agent Catalog and Agent Tracer. ([Couchbase Docs](https://docs.couchbase.com/ai/get-started/intro.html))

The central product bet is that banking AI is strongest when it operates directly on **live operational data plus governed context**, rather than as a disconnected copiloting layer.

---

## **3\. Product Vision**

Create a banking intelligence platform where specialized agents continuously interpret customer, operational, and branch-level activity, then help humans make faster and better decisions with full auditability.

---

## **4\. Users and Jobs to Be Done**

Internal users dominate the first release:

* fraud analysts  
* underwriters  
* branch/regional managers  
* contact center leads  
* financial advisors  
* compliance reviewers

The customer-facing surface is limited to advisor-approved recommendations and follow-up nudges.

---

## **5\. Multi-Agent Architecture**

### **Architecture pattern**

A **supervisor-orchestrated, specialist-agent model** is the best fit:

* **Supervisor service** handles routing, policy guardrails, and shared context assembly  
* **Specialist agents** execute narrow reasoning tasks  
* **Deterministic tools/services** perform reads, aggregations, and writes  
* **Human review gates** stop sensitive actions

### **Text-based architecture diagram**

\[Core Banking / CRM / Loan LOS / Branch KPI Feeds / Contact Center\]  
                    |  
                    v  
         \[Ingestion \+ Event Processing Layer\]  
                    |  
                    v  
      \[Couchbase Capella Operational Clusters\]  
   buckets/scopes for customers, transactions, loans,  
   branches, interactions, cases, agent\_state, audit  
                    |  
         \+----------+-----------+  
         |                      |  
         v                      v  
\[Vector Search \+ SQL++ \+ AI Functions\]   \[AI Services Workflows\]  
         |                      |  
         \+----------+-----------+  
                    v  
         \[Capella Model Service\]  
                    |  
                    v  
 \[Supervisor / Orchestrator \+ Agent Catalog-integrated agents\]  
      |         |         |         |         |  
      v         v         v         v         v  
   Fraud    Sentiment    Loan     Branch    Advisory  
   Agent      Agent      Agent    Agent      Agent  
                    |  
                    v  
         \[Agent Tracer \+ Audit \+ Metrics\]  
                    |  
                    v  
         \[Analyst UI / Manager UI / Advisor UI\]

### **Agent responsibility matrix**

| Agent | Primary Inputs | Core Outputs | Human Gate |
| ----- | ----- | ----- | ----- |
| Fraud | transactions, devices, accounts, prior cases | risk score, evidence, recommended action | mandatory |
| Sentiment | transcripts, emails, complaints, survey text | sentiment, urgency, drivers, churn risk | optional escalation |
| Loan | application, docs, income, policy rules, fraud context | summary, missing items, exceptions, disposition recommendation | mandatory |
| Branch | branch KPIs, staffing, complaints, fraud clusters | anomaly cards, root-cause hypotheses, action suggestions | manager review |
| Advisory | profile, goals, cash flow, holdings, service sentiment | next-best actions, explainable advice draft | mandatory |

### **Shared memory/context model**

Use Capella as the shared state layer:

* `customer_profile`  
* `relationship_summary`  
* `case_context`  
* `agent_session_state`  
* `retrieval_chunks`  
* `action_history`

Agent Catalog is documented to work with Capella as profile, transactional, or vector store, which aligns with this design. ([Couchbase Docs](https://docs.couchbase.com/ai/build/integrate-agent-with-catalog.html))

---

## **6\. Agent-by-Agent Design**

### **Fraud Detection Analyst**

**Trigger:** suspicious transaction stream event or manual investigation  
**Tasks:** anomaly explanation, linked-entity retrieval, pattern comparison, case summarization  
**Outputs:** risk score, reasons, ring indicators, recommended next action  
**Persistence:** `fraud_alert`, `investigation_case`, `audit_event`  
**Checkpoint:** analyst approves hold/escalate/contact action

### **Customer Sentiment Analyzer**

**Trigger:** new transcript, complaint, survey, secure message  
**Tasks:** sentiment, urgency, dissatisfaction drivers, churn risk, entity extraction  
**Outputs:** sentiment label, summary, escalation recommendation  
**Persistence:** `interaction_analysis`, `customer_signal`  
**Checkpoint:** optional supervisor/escalation review

### **Loan Reviewer Agent**

**Trigger:** new or updated application  
**Tasks:** summarize profile, validate completeness, detect policy exceptions, compare against fraud signals  
**Outputs:** missing docs list, exception flags, underwriter-ready summary, recommended status  
**Persistence:** `loan_review_summary`, `loan_exception`, `audit_event`  
**Checkpoint:** underwriter approval required

### **Branch Performance Monitor**

**Trigger:** scheduled KPI refresh or anomaly threshold breach  
**Tasks:** detect branch outliers, correlate with staffing/service/fraud/complaint signals  
**Outputs:** issue cards, likely causes, ranked recommendations  
**Persistence:** `branch_insight`, `branch_alert`  
**Checkpoint:** branch or regional manager review

### **Financial Advisory Companion**

**Trigger:** advisor opens workspace or scheduled relationship review  
**Tasks:** synthesize goals, savings, spending, products, recent service issues, and suitability rules  
**Outputs:** advice draft, next-best actions, follow-up nudges, explanation  
**Persistence:** `advice_draft`, `advisor_action_plan`  
**Checkpoint:** advisor must approve before customer delivery

---

## **7\. Data Model and Couchbase Schema**

### **Bucket / scope / collection summary**

| Bucket | Scope | Collections |
| ----- | ----- | ----- |
| `banking-core` | `customers` | `profiles`, `households`, `preferences` |
| `banking-core` | `transactions` | `ledger_events`, `cards`, `devices`, `merchant_links` |
| `banking-core` | `loans` | `applications`, `documents`, `reviews`, `policy_refs` |
| `banking-core` | `branches` | `kpis`, `staffing`, `alerts` |
| `banking-core` | `interactions` | `transcripts`, `emails`, `complaints`, `analysis` |
| `banking-core` | `agents` | `session_state`, `case_context`, `recommendations` |
| `banking-core` | `audit` | `events`, `approvals`, `overrides` |
| `banking-core` | `knowledge` | `retrieval_chunks`, `prompt_versions`, `tool_registry_cache` |

Capella AI Services Workflows can preprocess and vectorize structured and unstructured data, and store workflow metadata in a `vectorization-meta-data` scope while creating Eventing functions on the linked operational cluster. ([Couchbase Docs](https://docs.couchbase.com/ai/build/vectorization-service/data-processing.html))

### **Example JSON objects**

{  
  "type": "customer\_profile",  
  "customer\_id": "C12345",  
  "household\_id": "H982",  
  "name": "Asha Mehta",  
  "risk\_tolerance": "moderate",  
  "products": \["checking", "credit\_card", "auto\_loan"\],  
  "goals": \["emergency\_fund", "college\_savings"\],  
  "kyc\_status": "verified",  
  "last\_sentiment\_status": "negative"  
}

{  
  "type": "transaction\_event",  
  "txn\_id": "T99812",  
  "customer\_id": "C12345",  
  "account\_id": "A778",  
  "amount": 4200.55,  
  "merchant": "MERCHANT\_7781",  
  "channel": "card\_present",  
  "device\_id": "D991",  
  "geo": {"lat": 37.39, "lon": \-122.08},  
  "event\_ts": "2026-04-15T18:42:13Z"  
}

{  
  "type": "fraud\_alert",  
  "alert\_id": "FRAUD-441",  
  "txn\_id": "T99812",  
  "customer\_id": "C12345",  
  "risk\_score": 0.91,  
  "reasons": \["velocity\_spike", "new\_device", "merchant\_cluster\_match"\],  
  "recommended\_action": "manual\_hold\_review",  
  "status": "pending\_analyst\_review"  
}

{  
  "type": "loan\_application",  
  "application\_id": "L22011",  
  "customer\_id": "C12345",  
  "loan\_type": "personal",  
  "requested\_amount": 25000,  
  "stated\_income": 120000,  
  "submitted\_docs": \["paystub", "id\_doc"\],  
  "status": "submitted"  
}

{  
  "type": "interaction\_analysis",  
  "interaction\_id": "INT-887",  
  "customer\_id": "C12345",  
  "source": "call\_transcript",  
  "sentiment": "negative",  
  "urgency": "high",  
  "drivers": \["fee\_dispute", "long\_wait\_time"\],  
  "churn\_risk": 0.72,  
  "summary": "Customer expressed repeated frustration over fee reversal delays."  
}

{  
  "type": "audit\_event",  
  "event\_id": "AUD-9912",  
  "actor\_type": "human",  
  "actor\_id": "advisor\_17",  
  "related\_object\_id": "ADV-390",  
  "action": "approved\_recommendation",  
  "reason\_code": "suitable\_and\_explainable",  
  "ts": "2026-04-15T19:12:00Z"  
}

---

## **8\. Capella AI Services Usage**

| Capability | Capella Service | Usage in this product |
| ----- | ----- | ----- |
| LLM inference | Model Service | summaries, explanations, recommendation drafting |
| Embeddings | Model Service | vectorization for interactions, policies, documents |
| Data preprocessing | AI Services Workflows | process PDFs, DOCX, transcripts, JSON feeds |
| Retrieval | Vector Search | semantic retrieval across docs, interactions, and prior cases |
| In-query AI | AI Functions | sentiment, summarization, classification, extraction inside SQL++ |
| Agent management | Agent Catalog | tools/prompts registry, agent integration |
| Agent observability | Agent Tracer | session traces, tool calls, handoffs, debugging |
| AI admin / ops | AI Services APIs \+ dashboards | deployment, metrics, monitoring |

These capabilities are all documented by Couchbase. AI Functions support tasks such as sentiment analysis, summarization, classification, entity extraction, and more within SQL++ queries; Agent Tracer captures user, internal, LLM, tool call, tool result, handoff, and assistant traces; Model Service deploys LLMs and embedding models; and AI Services monitoring dashboards expose model and workflow metrics. ([Couchbase Docs](https://docs.couchbase.com/ai/build/ai-functions.html))

**Design choice:** even though some workflow and AI Function paths can integrate external providers, this application should use **Capella-hosted models only** to satisfy your constraint. Couchbase docs show optional external model support, but that is not required here. ([Couchbase Docs](https://docs.couchbase.com/ai/build/vectorization-service/vectorize-structured-data-capella.html))

---

## **9\. End-to-End Workflows**

1. **Fraud event**  
   * ingest transaction  
   * run deterministic pre-checks  
   * retrieve similar prior patterns  
   * LLM explains anomaly  
   * create alert and analyst task  
   * analyst approves action  
   * write audit trail  
2. **Complaint analysis**  
   * transcript lands in `interactions.transcripts`  
   * AI Function or model inference scores sentiment  
   * retrieval links prior complaints/policies  
   * customer signal updated  
   * advisor and branch monitor notified if threshold crossed  
3. **Loan review**  
   * application and docs ingested  
   * docs chunked/vectorized  
   * loan agent synthesizes profile and gaps  
   * fraud context queried  
   * underwriter reviews recommended disposition  
4. **Branch monitoring**  
   * scheduled KPI aggregation  
   * anomaly ranking  
   * customer complaints and fraud signals joined  
   * issue card generated for manager dashboard  
5. **Advisory assist**  
   * advisor opens customer 360  
   * system retrieves profile, goals, balances, sentiment, recent cases  
   * advisory agent drafts next-best actions  
   * advisor edits/approves  
   * approved recommendation stored and optionally delivered

---

## **10\. API and Backend Design**

### **Recommended stack**

* **Frontend:** React \+ TypeScript  
* **Backend:** Python \+ FastAPI  
* **Orchestration:** LangGraph-style agent workflow integrated with Agent Catalog  
* **Data access:** Couchbase Python SDK, SQL++, vector queries  
* **Async/eventing:** Kafka or event bus plus worker services  
* **Auth:** OIDC/SAML via enterprise IdP  
* **Telemetry:** OpenTelemetry \+ Agent Tracer \+ app metrics

### **REST API outline**

POST   /api/fraud/events  
GET    /api/fraud/alerts  
GET    /api/fraud/alerts/{id}  
POST   /api/fraud/alerts/{id}/approve

POST   /api/interactions/analyze  
GET    /api/customers/{id}/signals

POST   /api/loans/applications  
GET    /api/loans/applications/{id}/review  
POST   /api/loans/applications/{id}/decision

GET    /api/branches/{id}/insights  
GET    /api/branches/dashboard

GET    /api/advisory/customers/{id}/recommendations  
POST   /api/advisory/recommendations/{id}/approve

GET    /api/cases/{id}  
GET    /api/audit/{object\_id}  
GET    /api/metrics/agents

---

## **11\. UI/UX Concept**

### **Major screens**

1. **Operations Home**  
   alert feed, queue counts, SLA timers, branch watchlist  
2. **Fraud Workbench**  
   risk timeline, linked entities, similar historical cases, recommended actions  
3. **Customer Signals 360**  
   profile, product holdings, complaints, sentiment trend, churn indicators  
4. **Loan Review Workbench**  
   application summary, missing data, policy exceptions, fraud context, doc snippets  
5. **Branch Monitor Dashboard**  
   branch ranking, anomalies, staffing mismatches, complaint/fraud overlays  
6. **Advisor Workspace**  
   goals, balances, product gaps, advice draft, edit/approve flow  
7. **Audit & Trace Console**  
   human approvals, overrides, prompt version, tool call history, session traces

---

## **12\. Security, Governance, and Human-in-the-Loop Controls**

* RBAC by role, branch, region, and line of business  
* Mask PII when not required for task execution  
* Separate production, staging, and evaluation environments  
* Immutable audit events for approvals and overrides  
* Mandatory human approval for:  
  * fraud interventions  
  * loan recommendations converted to decisions  
  * customer-facing financial guidance  
* Trace every agent session and handoff through Agent Tracer; those traces can also be queried through SQL++ or Analytics. ([Couchbase Docs](https://docs.couchbase.com/ai/build/agent-tracer/agent-tracer.html))

---

## **13\. MVP Scope and Roadmap**

### **MVP**

* P0 fraud, sentiment, loan review  
* shared customer context  
* analyst/advisor/underwriter workbenches  
* audit trail and override logging  
* vectorized retrieval over policy and interaction content

### **Phase 2**

* deeper branch monitor  
* inter-agent proactive handoffs  
* advisor customer outreach queue  
* branch-to-fraud cluster correlation

### **Production hardening**

* red-team evaluation  
* calibration loops by agent  
* failover, backpressure controls, replayable event pipelines  
* advanced monitoring, cost controls, and capacity tuning

---

## **14\. Evaluation Framework**

| Dimension | Metrics |
| ----- | ----- |
| Fraud | precision, recall, false positives, case cycle time |
| Sentiment | classification agreement, escalation accuracy, churn-signal usefulness |
| Loan | completeness detection accuracy, exception precision, underwriter accept/edit rate |
| Branch | anomaly precision, root-cause usefulness, manager action rate |
| Advisory | recommendation acceptance, edit distance, suitability rejection rate |
| System | latency, trace completeness, retrieval hit quality, human override rate |

Use **offline evaluation sets**, **shadow mode**, and **human feedback capture** before expanding automation.

---

## **15\. Sample Scenarios**

1. **Fraud:** three debit cards tied to one household show unusual merchant velocity from a new device. Fraud agent opens a cluster case; branch monitor also sees a spike localized to one branch ATM corridor.  
2. **Sentiment:** repeated complaint transcripts reveal dissatisfaction with fee handling. Advisory agent suppresses cross-sell suggestions and recommends service recovery first.  
3. **Loan:** applicant submits income proof but misses bank statements. Loan agent flags incompleteness and a soft fraud inconsistency; underwriter receives a structured review pack.  
4. **Branch:** one branch shows declining sales, rising wait times, and increasing negative sentiment. Branch monitor attributes likely cause to staffing compression after schedule changes.  
5. **Advisory:** customer has strong cash flow but low emergency savings and recent dissatisfaction about overdraft fees. Advisor receives a savings-plan recommendation with a fee-reduction conversation prompt.

---

## **16\. Risks, Assumptions, and Open Questions**

### **Risks**

* AI explanations may sound plausible while missing critical facts  
* Retrieval quality may be weak if source data is noisy  
* Fraud workflows are especially sensitive to false positives  
* Advisory recommendations may be technically good but commercially or operationally mistimed

### **Assumptions**

* Bank can provide event streams and document access  
* Capella operational clusters are the primary operational data layer  
* Capella-hosted models are sufficient for the target tasks  
* Human reviewers are staffed for gated decisions

### **Open questions**

* Should household-level and SMB customer journeys be separate in v1?  
* What branch KPI granularity is available daily vs intraday?  
* Which policy rules should be deterministic vs model-assisted?  
* Should advisory outputs be limited to internal drafts for an extended period?

---

## **17\. Implementation Backlog**

### **Prioritized backlog**

| Priority | Epic | Sample User Stories |
| ----- | ----- | ----- |
| P0 | Data foundation | As a platform engineer, I can ingest transactions, profiles, applications, and transcripts into Capella with stable schemas |
| P0 | Fraud workbench | As a fraud analyst, I can view a ranked alert with evidence and approve/decline action |
| P0 | Loan review | As an underwriter, I can open a summarized file with missing items and exception flags |
| P0 | Sentiment pipeline | As a CX lead, I can view customer-level dissatisfaction signals from new interactions |
| P0 | Audit and approval | As a compliance reviewer, I can reconstruct every AI recommendation and human override |
| P1 | Shared customer 360 | As an advisor, I can see service, fraud, and product context in one workspace |
| P1 | Agent tracing | As an engineer, I can inspect prompts, tool calls, handoffs, and outputs for debugging |
| P1 | Branch insight cards | As a manager, I can view ranked branch anomalies with likely drivers |
| P2 | Customer delivery channel | As an advisor, I can send approved recommendations through supported channels |
| P2 | Proactive orchestration | As an ops lead, I can subscribe to inter-agent triggers and auto-create review tasks |

### **MVP acceptance criteria**

* Fraud, loan, and sentiment agents produce explainable case outputs with linked evidence  
* Human approval is enforced for sensitive actions  
* Customer 360 view merges operational and AI-derived signals  
* Retrieval corpus is searchable semantically through vector search  
* Prompt/tool/session traces are viewable for debugging  
* Audit logs reconstruct recommendation, approval, and override history end to end

If you want the next step, I can turn this into a **presentation-ready strategy deck** or a **PRFAQ-style product narrative**.

