"""
AI service interfaces — the contract between agents and inference backends.

Agents import only these ABCs. Capella/OpenAI/stub adapters implement them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_calls: list[dict] | None = None
    finish_reason: str = "stop"


@dataclass
class EmbeddingResponse:
    embedding: list[float]
    model: str
    token_count: int = 0


@dataclass
class RetrievalResult:
    chunk_id: str
    content: str
    source: str
    score: float
    metadata: dict = field(default_factory=dict)


class LLMService(ABC):
    """Generate text completions from a list of messages."""

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResponse: ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]: ...


class EmbeddingService(ABC):
    """Convert text to dense vector embeddings."""

    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResponse: ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResponse]: ...


class RetrievalService(ABC):
    """Semantic retrieval over the knowledge corpus stored in vector search."""

    @abstractmethod
    async def search(
        self,
        query: str,
        collection: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[RetrievalResult]: ...

    @abstractmethod
    async def index_chunk(
        self,
        chunk_id: str,
        text: str,
        collection: str,
        metadata: dict | None = None,
    ) -> None: ...
