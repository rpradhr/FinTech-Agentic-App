"""
Natural-language chat endpoint.

POST /api/chat/query
  - Accepts a plain-text message + optional conversation history
  - Classifies intent via LLM (keyword fallback when using stub adapter)
  - Fetches real data from repositories
  - Returns a structured ChatQueryResponse with agent_type, content, and cards
"""

from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.api.schemas import (
    ChatCard,
    ChatQueryRequest,
    ChatQueryResponse,
)
from app.core.container import get_container
from app.infrastructure.ai.interfaces import Message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# ─────────────────────────────────────────────────────────────────────────────
# Intent classification
# ─────────────────────────────────────────────────────────────────────────────

_CLASSIFY_SYSTEM = """You are an intent classifier for a banking operations assistant.
Given a user message, extract the intent and named entities as JSON.

Intent must be exactly one of:
  fraud_alerts    — user asks about fraud, suspicious transactions, or fraud alerts
  churn_risk      — user asks about customer churn, sentiment, or dissatisfaction
  loan_review     — user asks about loan applications or underwriting
  branch_insights — user asks about branch operations, wait times, or staffing
  advisory        — user asks about financial advice or product recommendations
  general         — anything else

Entities (all optional, null if not mentioned):
  customer_id    — e.g. "C-ASHA001"
  branch_id      — e.g. "BR-WEST01" or a branch name like "West Side"
  application_id — e.g. "L-001"
  alert_id       — e.g. "FRAUD-441"

Respond ONLY with valid JSON, no markdown, no explanation.
Example: {"intent":"fraud_alerts","entities":{"customer_id":"C-ASHA001","branch_id":null,"application_id":null,"alert_id":null}}"""

_BRANCH_NAME_MAP = {
    "west": "BR-WEST01",
    "east": "BR-EAST01",
    "north": "BR-NORTH01",
    "south": "BR-SOUTH01",
    "central": "BR-CENTRAL01",
    "downtown": "BR-DT01",
}


def _keyword_classify(text: str) -> dict:
    """Fallback classifier used when the LLM returns non-JSON (e.g. stub adapter)."""
    lower = text.lower()

    # ── Entity extraction ──────────────────────────────────────────────────
    customer_id = None
    branch_id = None
    application_id = None
    alert_id = None

    m = re.search(r"\bC-[A-Z0-9]+\b", text, re.IGNORECASE)
    if m:
        customer_id = m.group(0).upper()

    m = re.search(r"\bBR-[A-Z0-9]+\b", text, re.IGNORECASE)
    if m:
        branch_id = m.group(0).upper()
    elif not branch_id:
        for key, val in _BRANCH_NAME_MAP.items():
            if key in lower:
                branch_id = val
                break

    m = re.search(r"\bL-\d+\b", text, re.IGNORECASE)
    if m:
        application_id = m.group(0).upper()

    m = re.search(r"\bFRAUD-\d+\b", text, re.IGNORECASE)
    if m:
        alert_id = m.group(0).upper()

    # ── Intent ────────────────────────────────────────────────────────────
    if any(w in lower for w in ["fraud", "alert", "suspicious", "block", "velocity"]):
        intent = "fraud_alerts"
    elif any(w in lower for w in ["churn", "sentiment", "risk", "dissatisfied", "complaint"]):
        intent = "churn_risk"
    elif any(w in lower for w in ["loan", "application", "underwrite", "mortgage"]):
        intent = "loan_review"
    elif any(w in lower for w in ["branch", "staffing", "wait time", "kpi", "operations"]):
        intent = "branch_insights"
    elif any(w in lower for w in ["advi", "recommend", "savings", "investment", "product"]):
        intent = "advisory"
    else:
        intent = "general"

    return {
        "intent": intent,
        "entities": {
            "customer_id": customer_id,
            "branch_id": branch_id,
            "application_id": application_id,
            "alert_id": alert_id,
        },
    }


async def _classify(text: str, llm) -> dict:
    """Classify intent using the LLM; fall back to keyword matching on failure."""
    try:
        resp = await llm.complete(
            [
                Message(role="system", content=_CLASSIFY_SYSTEM),
                Message(role="user", content=text),
            ],
            temperature=0.0,
            max_tokens=200,
        )
        content = resp.content.strip()
        # Strip markdown code fences if the model wraps the JSON
        if content.startswith("```"):
            content = re.sub(r"```[a-z]*\n?", "", content).strip("`\n ")
        result = json.loads(content)
        if "intent" in result:
            return result
    except Exception:
        pass
    return _keyword_classify(text)


# ─────────────────────────────────────────────────────────────────────────────
# Colour helpers
# ─────────────────────────────────────────────────────────────────────────────

_RISK_COLORS: dict[str, str] = {
    "critical": "#c5221f",
    "high": "#ea4335",
    "medium": "#fbbc04",
    "low": "#34a853",
}


def _risk_color(level: str) -> str:
    return _RISK_COLORS.get(str(level).lower(), "#ea4335")


# ─────────────────────────────────────────────────────────────────────────────
# Intent handlers
# ─────────────────────────────────────────────────────────────────────────────


async def _fraud(entities: dict, container) -> ChatQueryResponse:
    alert_id = entities.get("alert_id")
    customer_id = entities.get("customer_id")

    if alert_id:
        a = await container.fraud.get_alert_by_id(alert_id)
        alerts = [a] if a else []
    elif customer_id:
        alerts = await container.fraud.get_alerts_by_customer(customer_id, limit=5)
    else:
        alerts = await container.fraud.list_pending_alerts(limit=5)

    if not alerts:
        subject = f"customer **{customer_id}**" if customer_id else "the system"
        return ChatQueryResponse(
            agent_type="fraud",
            content=f"No active fraud alerts found for {subject}.",
            cards=[],
        )

    subject = f"customer **{customer_id}**" if customer_id else "the system"
    top_score = max(a.risk_score for a in alerts)
    content = (
        f"Found **{len(alerts)} fraud alert{'s' if len(alerts) != 1 else ''}** for {subject}. "
        f"Highest risk score: **{top_score:.0%}**. Here's the breakdown:"
    )
    cards: list[ChatCard] = []
    for a in alerts[:3]:
        color = _risk_color(str(a.risk_level))
        cards.append(
            ChatCard(
                type="alert",
                title=f"{a.alert_id} · {str(a.risk_level).title()}",
                value=f"{a.risk_score:.0%} risk",
                subtitle=a.ai_explanation or a.recommended_action or "",
                status=str(a.status).replace("_", " "),
                items=(a.reasons or [])[:4],
                color=color,
            )
        )
    return ChatQueryResponse(agent_type="fraud", content=content, cards=cards)


async def _churn(entities: dict, container) -> ChatQueryResponse:
    customer_id = entities.get("customer_id")
    if not customer_id:
        return ChatQueryResponse(
            agent_type="sentiment",
            content=(
                "To check churn risk for a specific customer, include their ID "
                "(e.g. **C-ASHA001**) in your query. "
                "Alternatively, open the **Sentiment** tab for a full overview."
            ),
            cards=[],
        )

    signal = await container.customers.get_customer_signal(customer_id)
    if not signal:
        return ChatQueryResponse(
            agent_type="sentiment",
            content=f"No sentiment signal on record for **{customer_id}** yet.",
            cards=[],
        )

    color = (
        "#ea4335"
        if signal.churn_risk > 0.65
        else ("#fbbc04" if signal.churn_risk > 0.35 else "#34a853")
    )
    cards: list[ChatCard] = [
        ChatCard(
            type="metric",
            title=f"Customer {customer_id}",
            value=f"{signal.churn_risk:.0%} churn risk",
            subtitle=f"Sentiment: {signal.overall_sentiment}",
            status=signal.overall_sentiment,
            items=(signal.recent_drivers or [])[:4],
            color=color,
        )
    ]
    if signal.suppress_cross_sell:
        cards.append(
            ChatCard(
                type="summary",
                title="Cross-sell suppressed",
                subtitle=(
                    "Advisory cross-sell is automatically suppressed for this customer "
                    "until sentiment improves."
                ),
                color="#fbbc04",
            )
        )
    content = (
        f"Customer **{customer_id}** has a **{signal.churn_risk:.0%} churn risk** "
        f"with **{signal.overall_sentiment}** sentiment."
    )
    return ChatQueryResponse(agent_type="sentiment", content=content, cards=cards)


async def _loan(entities: dict, container) -> ChatQueryResponse:
    application_id = entities.get("application_id")

    if application_id:
        review = await container.loans.get_review_by_application(application_id)
        if not review:
            return ChatQueryResponse(
                agent_type="loan",
                content=f"No review found for loan application **{application_id}**.",
                cards=[],
            )
        status_str = str(review.recommended_status).replace("_", " ")
        color = (
            "#34a853"
            if "approve" in status_str
            else ("#fbbc04" if "pending" in status_str else "#ea4335")
        )
        cards: list[ChatCard] = [
            ChatCard(
                type="summary",
                title="Loan Review",
                subtitle=review.summary,
                status=status_str,
                color="#1a73e8",
            )
        ]
        if review.missing_documents:
            cards.append(
                ChatCard(
                    type="evidence",
                    title="Missing Documents",
                    items=review.missing_documents,
                    color="#fbbc04",
                )
            )
        cards.append(
            ChatCard(
                type="metric",
                title="AI Confidence",
                value=f"{review.confidence_score:.0%}",
                subtitle=review.ai_explanation or "",
                color=color,
            )
        )
        content = (
            f"Loan review for **{application_id}** (customer **{review.customer_id}**): "
            f"recommended status is **{status_str}** "
            f"with **{review.confidence_score:.0%}** confidence."
        )
        return ChatQueryResponse(agent_type="loan", content=content, cards=cards)

    # No application_id — list pending reviews
    reviews = await container.loans.list_pending_reviews(limit=5)
    if not reviews:
        return ChatQueryResponse(
            agent_type="loan",
            content="No pending loan reviews at this time.",
            cards=[],
        )
    cards = [
        ChatCard(
            type="summary",
            title=f"Review {r.review_id}",
            subtitle=(r.summary or "")[:120],
            status=str(r.recommended_status).replace("_", " "),
            color="#1a73e8",
        )
        for r in reviews[:3]
    ]
    return ChatQueryResponse(
        agent_type="loan",
        content=f"There are **{len(reviews)} pending loan review(s)**. Top entries:",
        cards=cards,
    )


async def _branch(entities: dict, container) -> ChatQueryResponse:
    branch_id = entities.get("branch_id")

    if branch_id:
        insights = await container.branches.get_insights_by_branch(branch_id, limit=3)
        alerts = await container.branches.list_branch_alerts(branch_id=branch_id, limit=5)

        if not insights and not alerts:
            return ChatQueryResponse(
                agent_type="branch",
                content=f"No recent insights or alerts for branch **{branch_id}**.",
                cards=[],
            )

        cards: list[ChatCard] = []
        for ins in insights[:2]:
            cards.append(
                ChatCard(
                    type="summary",
                    title=ins.issue_summary[:70],
                    items=(ins.probable_causes or [])[:3],
                    color="#fbbc04",
                )
            )
        for al in alerts[:2]:
            sev_color = {
                "critical": "#c5221f",
                "high": "#ea4335",
                "warning": "#fbbc04",
            }.get(str(al.severity).lower(), "#5f6368")
            cards.append(
                ChatCard(
                    type="alert",
                    title=al.description[:70],
                    status=str(al.severity),
                    color=sev_color,
                )
            )
        content = (
            f"Branch **{branch_id}** has **{len(insights)} recent insight(s)** "
            f"and **{len(alerts)} active alert(s)**."
        )
        return ChatQueryResponse(agent_type="branch", content=content, cards=cards)

    # Dashboard overview
    dashboard = await container.branches.list_branches_dashboard()
    if not dashboard:
        return ChatQueryResponse(
            agent_type="branch",
            content="No branch data available. Try running a branch analysis first.",
            cards=[],
        )
    cards = [
        ChatCard(
            type="metric",
            title=d.get("branch_name") or d.get("branch_id", "Unknown"),
            value=(
                f"{d['avg_wait_time_minutes']:.1f} min avg wait"
                if d.get("avg_wait_time_minutes")
                else "N/A"
            ),
            subtitle=(
                f"{d.get('complaint_count', 0)} complaints · "
                f"{d.get('new_accounts_opened', 0)} new accounts"
            ),
            color="#137333",
        )
        for d in dashboard[:4]
    ]
    return ChatQueryResponse(
        agent_type="branch",
        content=f"Branch operations dashboard across **{len(dashboard)} branch(es)**:",
        cards=cards,
    )


async def _advisory(entities: dict, container) -> ChatQueryResponse:
    customer_id = entities.get("customer_id")
    if not customer_id:
        return ChatQueryResponse(
            agent_type="advisory",
            content=(
                "To view financial advice, include the customer ID "
                "(e.g. **C-ASHA001**). All drafts require advisor approval before "
                "reaching the customer."
            ),
            cards=[],
        )

    drafts = await container.advisory.get_drafts_by_customer(customer_id, limit=1)
    if not drafts:
        return ChatQueryResponse(
            agent_type="advisory",
            content=(
                f"No advice drafts on record for **{customer_id}**. "
                "Open the **Advisory Workspace** to generate a new recommendation draft."
            ),
            cards=[],
        )

    draft = drafts[0]
    cards: list[ChatCard] = []
    if draft.suppress_cross_sell:
        cards.append(
            ChatCard(
                type="alert",
                title="Cross-sell suppressed",
                subtitle="Sentiment is elevated — service recovery should come first.",
                color="#ea4335",
            )
        )
    for action in (draft.next_best_actions or [])[:3]:
        cards.append(
            ChatCard(
                type="action",
                title=action.title,
                subtitle=action.rationale,
                items=action.evidence[:2] if action.evidence else [],
                color="#1a73e8",
            )
        )
    cards.append(
        ChatCard(
            type="metric",
            title="HITL Gate",
            value="Advisor approval required",
            subtitle="No recommendation reaches the customer without your sign-off.",
            color="#5f6368",
        )
    )
    content = (
        f"Advisory draft for **{customer_id}** — status: **{draft.status}**. "
        + ("Cross-sell suppressed. " if draft.suppress_cross_sell else "")
        + "Here are the recommended actions:"
    )
    return ChatQueryResponse(agent_type="advisory", content=content, cards=cards)


def _general() -> ChatQueryResponse:
    return ChatQueryResponse(
        agent_type="supervisor",
        content=(
            "I can help you with **fraud alerts**, **customer churn risk**, "
            "**loan reviews**, **branch operations**, or **financial advisory**. "
            "Try:\n"
            "- *Show fraud alerts for C-ASHA001*\n"
            "- *What's the churn risk for customer C-ASHA001?*\n"
            "- *Review loan application L-001*\n"
            "- *What's happening at the West Side branch?*\n"
            "- *Generate advice for customer C-ASHA001*"
        ),
        cards=[],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Route handler
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/query", response_model=ChatQueryResponse)
async def chat_query(
    body: ChatQueryRequest,
    _user=Depends(get_current_user),
):
    """
    NL query: classify intent → fetch real data → return structured agent response.
    All authenticated users may call this endpoint (read-only).
    """
    container = get_container()

    classified = await _classify(body.message, container.llm)
    intent: str = classified.get("intent", "general")
    entities: dict = classified.get("entities", {})

    logger.info("Chat query: intent=%s entities=%s", intent, entities)

    if intent == "fraud_alerts":
        return await _fraud(entities, container)
    if intent == "churn_risk":
        return await _churn(entities, container)
    if intent == "loan_review":
        return await _loan(entities, container)
    if intent == "branch_insights":
        return await _branch(entities, container)
    if intent == "advisory":
        return await _advisory(entities, container)
    return _general()
