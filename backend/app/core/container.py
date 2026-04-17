"""
Dependency injection container.

A single Container instance is created at application startup and wired into
FastAPI's dependency injection via `Depends(get_container)`.

All application services and repositories are resolved here — never constructed
inline in route handlers.
"""

from __future__ import annotations

import logging

from app.core.config import DatabaseBackend, Settings
from app.infrastructure.ai.interfaces import EmbeddingService, LLMService, RetrievalService
from app.infrastructure.ai.stub import StubEmbeddingService, StubLLMService, StubRetrievalService
from app.infrastructure.persistence.interfaces import (
    AdvisoryRepository,
    AuditRepository,
    BranchRepository,
    CaseRepository,
    CustomerRepository,
    FraudRepository,
    InteractionRepository,
    LoanRepository,
    TraceRepository,
    TransactionRepository,
)

logger = logging.getLogger(__name__)


class Container:
    """
    Holds fully-wired repository and service instances.

    Construction is synchronous; call `await container.connect()` once the
    event loop is running.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._connected = False

        # Resolve persistence backend
        if settings.database_backend == DatabaseBackend.COUCHBASE:
            self._init_couchbase()
        else:
            self._init_memory()

        # Resolve AI backend
        self._init_ai()

    # ──────────────────────────────────────────────────────────────────────
    # Persistence wiring
    # ──────────────────────────────────────────────────────────────────────

    def _init_memory(self) -> None:
        from app.infrastructure.persistence.memory import (
            InMemoryAdvisoryRepository,
            InMemoryAuditRepository,
            InMemoryBranchRepository,
            InMemoryCaseRepository,
            InMemoryCustomerRepository,
            InMemoryFraudRepository,
            InMemoryInteractionRepository,
            InMemoryLoanRepository,
            InMemoryStore,
            InMemoryTraceRepository,
            InMemoryTransactionRepository,
        )

        self._store = InMemoryStore()
        self.customers: CustomerRepository = InMemoryCustomerRepository(self._store)
        self.transactions: TransactionRepository = InMemoryTransactionRepository(self._store)
        self.fraud: FraudRepository = InMemoryFraudRepository(self._store)
        self.loans: LoanRepository = InMemoryLoanRepository(self._store)
        self.interactions: InteractionRepository = InMemoryInteractionRepository(self._store)
        self.branches: BranchRepository = InMemoryBranchRepository(self._store)
        self.cases: CaseRepository = InMemoryCaseRepository(self._store)
        self.advisory: AdvisoryRepository = InMemoryAdvisoryRepository(self._store)
        self.audit: AuditRepository = InMemoryAuditRepository(self._store)
        self.traces: TraceRepository = InMemoryTraceRepository(self._store)
        self._couchbase_client = None
        logger.info("Using in-memory persistence backend")

    def _init_couchbase(self) -> None:
        from app.infrastructure.persistence.couchbase import (
            CouchbaseAdvisoryRepository,
            CouchbaseAuditRepository,
            CouchbaseBranchRepository,
            CouchbaseCaseRepository,
            CouchbaseClient,
            CouchbaseCustomerRepository,
            CouchbaseFraudRepository,
            CouchbaseInteractionRepository,
            CouchbaseLoanRepository,
            CouchbaseTraceRepository,
            CouchbaseTransactionRepository,
        )

        self._couchbase_client = CouchbaseClient(self.settings)  # type: ignore[assignment]
        self.customers = CouchbaseCustomerRepository(self._couchbase_client)  # type: ignore[arg-type]
        self.transactions = CouchbaseTransactionRepository(  # type: ignore[assignment]
            self._couchbase_client  # type: ignore[arg-type]
        )
        self.fraud = CouchbaseFraudRepository(self._couchbase_client)  # type: ignore[assignment, arg-type]
        self.loans = CouchbaseLoanRepository(self._couchbase_client)  # type: ignore[assignment, arg-type]
        self.interactions = CouchbaseInteractionRepository(  # type: ignore[assignment]
            self._couchbase_client  # type: ignore[arg-type]
        )
        self.branches = CouchbaseBranchRepository(self._couchbase_client)  # type: ignore[assignment, arg-type]
        self.cases = CouchbaseCaseRepository(self._couchbase_client)  # type: ignore[assignment, arg-type]
        self.advisory = CouchbaseAdvisoryRepository(self._couchbase_client)  # type: ignore[assignment, arg-type]
        self.audit = CouchbaseAuditRepository(self._couchbase_client)  # type: ignore[assignment, arg-type]
        self.traces = CouchbaseTraceRepository(self._couchbase_client)  # type: ignore[assignment, arg-type]
        logger.info("Using Couchbase persistence backend")

    # ──────────────────────────────────────────────────────────────────────
    # AI wiring
    # ──────────────────────────────────────────────────────────────────────

    def _init_ai(self) -> None:
        if self.settings.use_capella_ai or self.settings.openai_api_key:
            from app.infrastructure.ai.capella import (
                CapellaEmbeddingService,
                CapellaLLMService,
                CapellaRetrievalService,
            )

            self.llm: LLMService = CapellaLLMService(self.settings)
            self.embeddings: EmbeddingService = CapellaEmbeddingService(self.settings)
            if self._couchbase_client:
                self.retrieval: RetrievalService = CapellaRetrievalService(
                    self.settings, self.embeddings, self._couchbase_client
                )
            else:
                self.retrieval = StubRetrievalService()
            logger.info("Using Capella/OpenAI AI backend")
        else:
            self.llm = StubLLMService()
            self.embeddings = StubEmbeddingService()
            self.retrieval = StubRetrievalService()
            logger.info("Using stub AI backend (no credentials configured)")

    # ──────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        if self._couchbase_client:
            await self._couchbase_client.connect()
        self._connected = True

    async def close(self) -> None:
        if self._couchbase_client:
            await self._couchbase_client.close()


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton — set by app.main on startup
# ─────────────────────────────────────────────────────────────────────────────
_container: Container | None = None


def set_container(c: Container) -> None:
    global _container
    _container = c


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized. Did startup complete?")
    return _container
