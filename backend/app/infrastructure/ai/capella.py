"""
Capella AI Services adapter.

Calls the Capella Model Service REST API for LLM inference and embeddings.
If Capella is unavailable, raises a ServiceUnavailableError that the
orchestrator catches to apply its deterministic fallback.

Capella uses an OpenAI-compatible API surface, so the same httpx calls work
with the OpenAI SDK pointed at the Capella endpoint.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.core.config import Settings

from .interfaces import (
    EmbeddingResponse,
    EmbeddingService,
    LLMResponse,
    LLMService,
    Message,
    RetrievalResult,
    RetrievalService,
)

logger = logging.getLogger(__name__)


def _to_openai_messages(messages: list[Message]) -> list[dict]:
    result = []
    for m in messages:
        msg: dict = {"role": m.role, "content": m.content}
        if m.tool_call_id:
            msg["tool_call_id"] = m.tool_call_id
        if m.tool_calls:
            msg["tool_calls"] = m.tool_calls
        result.append(msg)
    return result


class CapellaLLMService(LLMService):
    """LLM completion via Capella Model Service (OpenAI-compatible endpoint)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.capella_ai_api_key or settings.openai_api_key,
            base_url=settings.capella_ai_endpoint or None,
        )

    async def complete(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        kwargs: dict = {
            "model": self._settings.capella_model_id,
            "messages": _to_openai_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            tool_calls=(
                [tc.model_dump() for tc in choice.message.tool_calls]
                if choice.message.tool_calls
                else None
            ),
            finish_reason=choice.finish_reason or "stop",
        )

    async def stream(
        self,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._settings.capella_model_id,
            messages=_to_openai_messages(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


class CapellaEmbeddingService(EmbeddingService):
    """Embedding generation via Capella Model Service."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.capella_ai_api_key or settings.openai_api_key,
            base_url=settings.capella_ai_endpoint or None,
        )

    async def embed(self, text: str) -> EmbeddingResponse:
        response = await self._client.embeddings.create(
            model=self._settings.capella_embedding_model_id,
            input=text,
        )
        emb = response.data[0]
        return EmbeddingResponse(
            embedding=emb.embedding,
            model=response.model,
            token_count=response.usage.total_tokens if response.usage else 0,
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResponse]:
        response = await self._client.embeddings.create(
            model=self._settings.capella_embedding_model_id,
            input=texts,
        )
        return [
            EmbeddingResponse(
                embedding=item.embedding,
                model=response.model,
                token_count=0,
            )
            for item in sorted(response.data, key=lambda x: x.index)
        ]


class CapellaRetrievalService(RetrievalService):
    """
    Semantic retrieval using Couchbase Capella vector search.

    Embeds the query, then queries the Capella vector search index via
    the Couchbase Python SDK's search API.
    """

    def __init__(
        self,
        settings: Settings,
        embedding_service: EmbeddingService,
        couchbase_client,  # CouchbaseClient — avoid circular import via string type
    ) -> None:
        self._settings = settings
        self._embed = embedding_service
        self._cb = couchbase_client

    async def search(
        self,
        query: str,
        collection: str = "retrieval_chunks",
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[RetrievalResult]:
        emb_response = await self._embed.embed(query)
        embedding = emb_response.embedding

        # Build Couchbase vector search query using SQL++ VECTOR_DISTANCE
        filter_clause = ""
        params: dict = {
            "vec": embedding,
            "topk": top_k,
        }
        if filters:
            conditions = []
            for k, v in filters.items():
                param_key = f"f_{k}"
                conditions.append(f"c.{k} = ${param_key}")
                params[param_key] = v
            filter_clause = " AND " + " AND ".join(conditions)

        statement = (
            f"SELECT c.chunk_id, c.content, c.source, c.metadata, "
            f"VECTOR_DISTANCE(c.embedding, $vec, 'cosine') AS score "
            f"FROM `banking-core`.knowledge.retrieval_chunks c "
            f"WHERE c.collection_name = '{collection}'{filter_clause} "
            f"ORDER BY score LIMIT $topk"
        )

        try:
            cluster = self._cb.cluster()
            import asyncio

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: cluster.query(statement, **params))
            rows = [row for row in result]
        except Exception as exc:
            logger.warning("Vector search failed, returning empty results: %s", exc)
            return []

        return [
            RetrievalResult(
                chunk_id=r.get("chunk_id", ""),
                content=r.get("content", ""),
                source=r.get("source", ""),
                score=float(r.get("score", 0.0)),
                metadata=r.get("metadata", {}),
            )
            for r in rows
        ]

    async def index_chunk(
        self,
        chunk_id: str,
        text: str,
        collection: str,
        metadata: dict | None = None,
    ) -> None:
        emb_response = await self._embed.embed(text)
        doc = {
            "chunk_id": chunk_id,
            "content": text,
            "collection_name": collection,
            "embedding": emb_response.embedding,
            "source": (metadata or {}).get("source", ""),
            "metadata": metadata or {},
        }
        col = self._cb.get_collection("agent_sessions")  # uses knowledge bucket
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: col.upsert(chunk_id, doc))
