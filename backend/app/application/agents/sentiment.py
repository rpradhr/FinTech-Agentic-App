"""
Customer Sentiment Analyzer Agent.

Inputs:  Interaction (transcript, email, complaint, survey)
Outputs: InteractionAnalysis with sentiment, urgency, drivers, churn risk
Gate:    Optional escalation review (supervisor trigger if churn_risk > threshold)
"""

from __future__ import annotations

import json
import logging

from app.core.ids import new_analysis_id, new_audit_id, new_session_id
from app.domain.models import (
    CustomerSignal,
    Interaction,
    InteractionAnalysis,
)
from app.domain.models.audit import AuditAction
from app.domain.models.interaction import SentimentLabel, UrgencyLevel
from app.infrastructure.ai.interfaces import LLMService, Message, RetrievalService
from app.infrastructure.persistence.interfaces import (
    AuditRepository,
    CustomerRepository,
    InteractionRepository,
    TraceRepository,
)

from .base import BaseAgent

logger = logging.getLogger(__name__)

SENTIMENT_SYSTEM_PROMPT = """You are a customer experience analyst at a retail bank.
Analyze customer interactions to identify sentiment, urgency, dissatisfaction drivers, and churn risk.

Return ONLY a valid JSON object:
{
  "sentiment": <"very_positive"|"positive"|"neutral"|"negative"|"very_negative">,
  "sentiment_score": <float -1.0 to 1.0>,
  "urgency": <"low"|"medium"|"high"|"critical">,
  "drivers": [<string>, ...],
  "churn_risk": <float 0.0-1.0>,
  "escalation_recommended": <boolean>,
  "summary": <string — 1-2 sentences for the CX team>,
  "entities_mentioned": [<string>, ...]
}

Drivers should be concise labels like: fee_dispute, long_wait_time, product_issue,
error_resolution_delay, staff_attitude, overdraft_frustration, etc.
"""

CHURN_RISK_ESCALATION_THRESHOLD = 0.65


class SentimentAgent(BaseAgent):
    """Analyzes customer interactions for sentiment, urgency, and churn risk."""

    name = "sentiment_agent"

    def __init__(
        self,
        llm: LLMService,
        retrieval: RetrievalService,
        audit_repo: AuditRepository,
        trace_repo: TraceRepository,
        interaction_repo: InteractionRepository,
        customer_repo: CustomerRepository,
    ) -> None:
        super().__init__(llm, retrieval, audit_repo, trace_repo)
        self._interactions = interaction_repo
        self._customers = customer_repo

    async def analyze_interaction(
        self, interaction: Interaction, session_id: str | None = None
    ) -> InteractionAnalysis:
        """
        Analyze a single customer interaction and produce an InteractionAnalysis.
        Updates the customer's aggregated CustomerSignal.
        """
        session_id = session_id or new_session_id()
        step = 0

        # 1. Get customer context
        customer = await self._customers.get_by_id(interaction.customer_id)
        recent_analyses = await self._interactions.get_recent_analyses_by_customer(
            interaction.customer_id, limit=5
        )

        # 2. Retrieve relevant complaint policies
        policy_ctx = await self._retrieve_context(
            "customer complaint handling escalation policy",
            collection="cx_policies",
        )

        # 3. Build prompt
        context = self._build_prompt(interaction, customer, recent_analyses, policy_ctx)
        messages = [
            Message(role="system", content=SENTIMENT_SYSTEM_PROMPT),
            Message(role="user", content=context),
        ]

        # 4. Call LLM
        raw_output = await self._complete(messages, session_id, step)
        step += 1

        # 5. Parse
        result = self._parse_result(raw_output)

        # 6. Build analysis object
        analysis = InteractionAnalysis(
            analysis_id=new_analysis_id(),
            interaction_id=interaction.interaction_id,
            customer_id=interaction.customer_id,
            source=interaction.source,
            sentiment=result.get("sentiment", SentimentLabel.NEUTRAL),
            sentiment_score=result.get("sentiment_score", 0.0),
            urgency=result.get("urgency", UrgencyLevel.LOW),
            drivers=result.get("drivers", []),
            churn_risk=result.get("churn_risk", 0.0),
            escalation_recommended=result.get("escalation_recommended", False),
            summary=result.get("summary", ""),
            entities_mentioned=result.get("entities_mentioned", []),
        )

        # 7. Persist
        await self._interactions.save_analysis(analysis)

        # 8. Update aggregated customer signal
        await self._update_customer_signal(interaction.customer_id, analysis, recent_analyses)

        # 9. Audit
        await self._emit_audit(
            event_id=new_audit_id(),
            action=AuditAction.SENTIMENT_ANALYSIS_CREATED,
            actor_id=self.name,
            related_object_id=analysis.analysis_id,
            related_object_type="interaction_analysis",
            customer_id=interaction.customer_id,
            session_id=session_id,
            input_summary=f"Interaction {interaction.interaction_id} source={interaction.source}",
            output_summary=(
                f"Sentiment={analysis.sentiment} churn_risk={analysis.churn_risk:.2f} "
                f"escalation={analysis.escalation_recommended}"
            ),
        )

        logger.info(
            "Sentiment analysis complete",
            extra={
                "analysis_id": analysis.analysis_id,
                "sentiment": analysis.sentiment,
                "churn_risk": analysis.churn_risk,
            },
        )
        return analysis

    async def _update_customer_signal(
        self, customer_id: str, new_analysis: InteractionAnalysis, prior_analyses: list
    ) -> None:
        """Roll up the latest N analyses into a CustomerSignal."""
        signal = await self._customers.get_customer_signal(customer_id) or CustomerSignal(
            customer_id=customer_id
        )
        all_analyses = [new_analysis] + list(prior_analyses)
        if all_analyses:
            avg_risk = sum(a.churn_risk for a in all_analyses) / len(all_analyses)
            signal.churn_risk = min(avg_risk, 1.0)
            signal.overall_sentiment = new_analysis.sentiment
            signal.recent_drivers = list({d for a in all_analyses[:3] for d in a.drivers})
        signal.suppress_cross_sell = signal.churn_risk > CHURN_RISK_ESCALATION_THRESHOLD
        await self._customers.save_customer_signal(signal)
        # Also update the customer profile's top-level sentiment
        await self._customers.update_sentiment(
            customer_id, new_analysis.sentiment, signal.churn_risk
        )

    def _build_prompt(self, interaction, customer, recent_analyses, policy_ctx) -> str:
        parts = [
            "## Interaction to Analyze",
            f"- ID: {interaction.interaction_id}",
            f"- Source: {interaction.source}",
            f"- Content:\n\n{interaction.content}\n",
        ]
        if customer:
            parts += [
                "## Customer Context",
                f"- Risk tolerance: {customer.risk_tolerance}",
                f"- Products: {customer.products}",
                f"- Last sentiment: {customer.last_sentiment_status}",
            ]
        if recent_analyses:
            parts.append("## Recent Interaction Analyses")
            for a in recent_analyses:
                parts.append(
                    f"  - {a.analysis_id}: sentiment={a.sentiment} "
                    f"drivers={a.drivers} churn={a.churn_risk:.2f}"
                )
        if policy_ctx:
            parts.append(f"## Escalation Policy Context\n{policy_ctx}")
        return "\n".join(parts)

    def _parse_result(self, raw: str) -> dict:
        try:
            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            return json.loads(text)
        except Exception:
            logger.warning("Failed to parse sentiment agent output")
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "urgency": "low",
                "drivers": [],
                "churn_risk": 0.0,
                "escalation_recommended": False,
                "summary": "Unable to parse AI output.",
                "entities_mentioned": [],
            }
