"""
Branch Performance Monitor Agent.

Inputs:  BranchKPI snapshots, complaint analyses, fraud-flagged transactions
Outputs: BranchInsight with anomaly cards, root-cause hypotheses, recommendations
Gate:    Branch/regional manager review
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from app.core.ids import new_audit_id, new_branch_insight_id, new_id, new_session_id
from app.domain.models import BranchAlert, BranchInsight
from app.domain.models.branch import BranchAlertSeverity
from app.infrastructure.ai.interfaces import LLMService, Message, RetrievalService
from app.infrastructure.persistence.interfaces import (
    AuditRepository,
    BranchRepository,
    InteractionRepository,
    TraceRepository,
    TransactionRepository,
)

from .base import BaseAgent

logger = logging.getLogger(__name__)

BRANCH_SYSTEM_PROMPT = """You are a branch operations analyst at a retail bank.
Review branch KPI data and correlated signals to identify anomalies and likely root causes.

Return ONLY a valid JSON object:
{
  "issue_summary": <string — 1-2 sentences for the dashboard card>,
  "probable_causes": [<string>, ...],
  "ranked_recommendations": [<string>, ...],
  "supporting_signals": {<key>: <value>, ...},
  "anomaly_types": [<string>, ...]
}

Probable causes should be specific (e.g., "staffing reduction of 2 FTEs on Mon/Tue")
not generic (e.g., "staffing issues").
"""


class BranchAgent(BaseAgent):
    """Branch Performance Monitor — detects anomalies and generates insight cards."""

    name = "branch_agent"

    def __init__(
        self,
        llm: LLMService,
        retrieval: RetrievalService,
        audit_repo: AuditRepository,
        trace_repo: TraceRepository,
        branch_repo: BranchRepository,
        interaction_repo: InteractionRepository,
        transaction_repo: TransactionRepository,
    ) -> None:
        super().__init__(llm, retrieval, audit_repo, trace_repo)
        self._branches = branch_repo
        self._interactions = interaction_repo
        self._transactions = transaction_repo

    async def analyze_branch(
        self, branch_id: str, session_id: str | None = None
    ) -> BranchInsight | None:
        """
        Run anomaly analysis on a branch using recent KPIs and correlated signals.
        Returns None if no anomaly is detected.
        """
        session_id = session_id or new_session_id()
        step = 0

        # 1. Get KPI history
        recent_kpis = await self._branches.get_recent_kpis(branch_id, days=14)
        if not recent_kpis:
            logger.info("No KPI data for branch %s", branch_id)
            return None

        # 2. Deterministic anomaly pre-check
        anomaly_flags = self._detect_anomalies(recent_kpis)
        if not anomaly_flags:
            logger.debug("No anomalies detected for branch %s", branch_id)
            return None

        # 3. Get complaint analyses for this branch
        await self._interactions.get_interactions_by_customer(
            branch_id,
            limit=20,  # branch_id used as a proxy filter here
        )

        # 4. Get fraud-flagged transactions
        since = datetime.utcnow() - timedelta(days=7)
        fraud_txns = await self._transactions.get_flagged_by_branch(branch_id, since=since)

        # 5. Retrieve ops best-practice context
        policy_ctx = await self._retrieve_context(
            "branch performance improvement staffing complaints",
            collection="branch_policies",
        )

        # 6. Build prompt
        context = self._build_prompt(branch_id, recent_kpis, anomaly_flags, fraud_txns, policy_ctx)
        messages = [
            Message(role="system", content=BRANCH_SYSTEM_PROMPT),
            Message(role="user", content=context),
        ]

        # 7. Call LLM
        raw_output = await self._complete(messages, session_id, step)
        step += 1

        # 8. Parse
        result = self._parse_result(raw_output)

        # 9. Create alerts for each anomaly type
        alert_ids = []
        for anomaly_type in result.get("anomaly_types", anomaly_flags):
            alert = BranchAlert(
                alert_id=new_id("BRA-"),
                branch_id=branch_id,
                severity=self._infer_severity(anomaly_type),
                anomaly_type=anomaly_type,
                description=result.get("issue_summary", anomaly_type),
            )
            saved = await self._branches.save_alert(alert)
            alert_ids.append(saved.alert_id)

        # 10. Build insight
        insight = BranchInsight(
            insight_id=new_branch_insight_id(),
            branch_id=branch_id,
            trigger_alert_ids=alert_ids,
            issue_summary=result.get("issue_summary", ""),
            probable_causes=result.get("probable_causes", []),
            ranked_recommendations=result.get("ranked_recommendations", []),
            supporting_signals=result.get("supporting_signals", {}),
        )

        saved_insight = await self._branches.save_insight(insight)

        # 11. Audit
        await self._emit_audit(
            event_id=new_audit_id(),
            action="branch_insight_created",
            actor_id=self.name,
            related_object_id=insight.insight_id,
            related_object_type="branch_insight",
            session_id=session_id,
            output_summary=f"Branch {branch_id}: {len(anomaly_flags)} anomaly types detected",
        )

        return saved_insight

    def _detect_anomalies(self, kpis: list) -> list[str]:
        """Simple deterministic checks — supplement LLM analysis."""
        flags = []
        if len(kpis) < 2:
            return flags
        latest = kpis[0]
        prev_avg_wait = sum(k.avg_wait_time_minutes or 0 for k in kpis[1:]) / max(len(kpis) - 1, 1)
        if (
            latest.avg_wait_time_minutes
            and prev_avg_wait > 0
            and latest.avg_wait_time_minutes > prev_avg_wait * 1.4
        ):
            flags.append("wait_time_spike")
        if latest.complaint_count > 5:
            flags.append("complaint_surge")
        if latest.scheduled_staff > 0 and latest.actual_staff < latest.scheduled_staff * 0.8:
            flags.append("staffing_gap")
        prev_avg_accounts = sum(k.new_accounts_opened for k in kpis[1:]) / max(len(kpis) - 1, 1)
        if prev_avg_accounts > 0 and latest.new_accounts_opened < prev_avg_accounts * 0.6:
            flags.append("sales_decline")
        return flags

    def _infer_severity(self, anomaly_type: str) -> BranchAlertSeverity:
        if anomaly_type in ("complaint_surge", "staffing_gap"):
            return BranchAlertSeverity.WARNING
        if anomaly_type == "fraud_cluster":
            return BranchAlertSeverity.CRITICAL
        return BranchAlertSeverity.INFO

    def _build_prompt(self, branch_id, kpis, anomaly_flags, fraud_txns, policy_ctx) -> str:
        latest = kpis[0]
        parts = [
            f"## Branch: {branch_id}",
            f"## Detected Anomaly Flags: {anomaly_flags}",
            f"\n## Latest KPI Snapshot ({latest.report_date})",
            f"- Avg wait time: {latest.avg_wait_time_minutes} min",
            f"- Complaints: {latest.complaint_count}",
            f"- New accounts: {latest.new_accounts_opened}",
            f"- Scheduled staff: {latest.scheduled_staff}  Actual: {latest.actual_staff}",
            f"- Teller transactions: {latest.teller_transactions}",
            f"\n## KPI Trend (last {len(kpis)} periods)",
        ]
        for k in kpis[:7]:
            parts.append(
                f"  - {k.report_date}: wait={k.avg_wait_time_minutes} "
                f"complaints={k.complaint_count} staff={k.actual_staff}"
            )
        if fraud_txns:
            parts.append(f"\n## Fraud-Flagged Transactions (last 7 days): {len(fraud_txns)}")
        if policy_ctx:
            parts.append(f"\n## Operations Context\n{policy_ctx}")
        return "\n".join(parts)

    def _parse_result(self, raw: str) -> dict:
        try:
            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            return json.loads(text)
        except Exception:
            logger.warning("Failed to parse branch agent output")
            return {
                "issue_summary": "Anomaly detected; AI output could not be parsed.",
                "probable_causes": [],
                "ranked_recommendations": [],
                "supporting_signals": {},
                "anomaly_types": [],
            }
