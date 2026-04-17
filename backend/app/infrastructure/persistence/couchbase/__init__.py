# Couchbase / Capella adapter — production persistence implementation.
from .client import CouchbaseClient
from .repositories import (
    CouchbaseCustomerRepository,
    CouchbaseTransactionRepository,
    CouchbaseFraudRepository,
    CouchbaseLoanRepository,
    CouchbaseInteractionRepository,
    CouchbaseBranchRepository,
    CouchbaseCaseRepository,
    CouchbaseAdvisoryRepository,
    CouchbaseAuditRepository,
    CouchbaseTraceRepository,
)

__all__ = [
    "CouchbaseClient",
    "CouchbaseCustomerRepository",
    "CouchbaseTransactionRepository",
    "CouchbaseFraudRepository",
    "CouchbaseLoanRepository",
    "CouchbaseInteractionRepository",
    "CouchbaseBranchRepository",
    "CouchbaseCaseRepository",
    "CouchbaseAdvisoryRepository",
    "CouchbaseAuditRepository",
    "CouchbaseTraceRepository",
]
