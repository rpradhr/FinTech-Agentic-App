"""
Base agent — shared tracing and audit utilities for all specialist agents.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.core.ids import new_trace_id
from app.domain.models.audit import AgentTrace, AuditAction, AuditActor, AuditEvent
from app.infrastructure.ai.interfaces import LLMService, Message, RetrievalService
from app.infrastructure.persistence.interfaces import AuditRepository, TraceRepository

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Shared base for all specialist agents.

    Provides:
    - LLM completion helper with automatic tracing
    - Audit event emission
    - Retrieval helper
    """

    name: str = "base_agent"

    def __init__(
        self,
        llm: LLMService,
        retrieval: RetrievalService,
        audit_repo: AuditRepository,
        trace_repo: TraceRepository,
    ) -> None:
        self._llm = llm
        self._retrieval = retrieval
        self._audit = audit_repo
        self._traces = trace_repo

    async def _complete(
        self,
        messages: list[Message],
        session_id: str,
        step_index: int,
        tools: list[dict] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        """Run LLM completion and record the trace step."""

        start = datetime.utcnow()
        response = await self._llm.complete(
            messages, tools=tools, temperature=temperature, max_tokens=max_tokens
        )
        latency_ms = (datetime.utcnow() - start).total_seconds() * 1000

        trace = AgentTrace(
            trace_id=new_trace_id(),
            session_id=session_id,
            agent_name=self.name,
            step_type="llm_call",
            step_index=step_index,
            input_data={
                "messages": [{"role": m.role, "content": m.content[:200]} for m in messages]
            },
            output_data={"content": response.content[:500]},
            model_id=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=latency_ms,
        )
        await self._traces.append_trace(trace)
        return response.content

    async def _emit_audit(
        self,
        event_id: str,
        action: AuditAction,
        actor_id: str,
        related_object_id: str,
        related_object_type: str,
        customer_id: str | None = None,
        session_id: str | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        event = AuditEvent(
            event_id=event_id,
            actor_type=AuditActor.AGENT,
            actor_id=self.name,
            action=action,
            related_object_id=related_object_id,
            related_object_type=related_object_type,
            customer_id=customer_id,
            agent_session_id=session_id,
            input_summary=input_summary,
            output_summary=output_summary,
            metadata=metadata or {},
        )
        await self._audit.append(event)

    async def _retrieve_context(
        self,
        query: str,
        collection: str = "retrieval_chunks",
        top_k: int = 3,
    ) -> str:
        """Return a formatted string of retrieved context chunks."""
        results = await self._retrieval.search(query, collection, top_k)
        if not results:
            return ""
        chunks = [f"[Source: {r.source}]\n{r.content}" for r in results]
        return "\n\n---\n\n".join(chunks)
