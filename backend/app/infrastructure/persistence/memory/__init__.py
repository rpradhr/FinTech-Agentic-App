# In-memory adapter — used for unit tests and local dev without a database.
from .repositories import (
    InMemoryCustomerRepository,
    InMemoryTransactionRepository,
    InMemoryFraudRepository,
    InMemoryLoanRepository,
    InMemoryInteractionRepository,
    InMemoryBranchRepository,
    InMemoryCaseRepository,
    InMemoryAdvisoryRepository,
    InMemoryAuditRepository,
    InMemoryTraceRepository,
)
from .store import InMemoryStore

__all__ = [
    "InMemoryStore",
    "InMemoryCustomerRepository",
    "InMemoryTransactionRepository",
    "InMemoryFraudRepository",
    "InMemoryLoanRepository",
    "InMemoryInteractionRepository",
    "InMemoryBranchRepository",
    "InMemoryCaseRepository",
    "InMemoryAdvisoryRepository",
    "InMemoryAuditRepository",
    "InMemoryTraceRepository",
]
