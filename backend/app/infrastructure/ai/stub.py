"""
Stub AI adapter — used in unit tests and local dev without AI credentials.

Returns deterministic, predictable responses.
"""
from __future__ import annotations

import random
from typing import AsyncIterator, Optional

from .interfaces import (
    EmbeddingResponse,
    EmbeddingService,
    LLMResponse,
    LLMService,
    Message,
    RetrievalResult,
    RetrievalService,
)


class StubLLMService(LLMService):
    """Returns a canned response without calling any external API."""

    def __init__(self, fixed_response: str = "Stub AI response.") -> None:
        self._response = fixed_response

    async def complete(
        self,
        messages: list[Message],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        return LLMResponse(
            content=self._response,
            model="stub",
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(self._response.split()),
        )

    async def stream(
        self,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        for word in self._response.split():
            yield word + " "


class StubEmbeddingService(EmbeddingService):
    """Returns a random unit-ish vector — shape is consistent per text hash."""

    DIMS = 1536

    async def embed(self, text: str) -> EmbeddingResponse:
        rng = random.Random(hash(text))
        vec = [rng.gauss(0, 1) for _ in range(self.DIMS)]
        norm = sum(v**2 for v in vec) ** 0.5
        return EmbeddingResponse(
            embedding=[v / norm for v in vec],
            model="stub-embedding",
            token_count=len(text.split()),
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResponse]:
        return [await self.embed(t) for t in texts]


class StubRetrievalService(RetrievalService):
    """Returns empty retrieval results."""

    async def search(
        self,
        query: str,
        collection: str = "retrieval_chunks",
        top_k: int = 5,
        filters: Optional[dict] = None,
    ) -> list[RetrievalResult]:
        return []

    async def index_chunk(
        self,
        chunk_id: str,
        text: str,
        collection: str,
        metadata: Optional[dict] = None,
    ) -> None:
        pass  # no-op in stub
