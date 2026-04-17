# Couchbase / Capella adapter — production persistence implementation.
from .client import CouchbaseClient
from .repositories import (
    CouchbaseAdvisoryRepository,
    CouchbaseAuditRepository,
    CouchbaseBranchRepository,
    CouchbaseCaseRepository,
    CouchbaseCustomerRepository,
    CouchbaseFraudRepository,
    CouchbaseInteractionRepository,
    CouchbaseLoanRepository,
    CouchbaseTraceRepository,
    CouchbaseTransactionRepository,
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
