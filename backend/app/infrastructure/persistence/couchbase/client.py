"""
Couchbase / Capella connection client.

Wraps the Couchbase Python SDK cluster + bucket objects and exposes
collection handles.  All Couchbase-specific SDK calls are confined here and
in the repository implementations — nothing leaks to application or domain.
"""

from __future__ import annotations

import asyncio
import logging

from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.collection import Collection
from couchbase.exceptions import CouchbaseException
from couchbase.options import ClusterOptions, ClusterTimeoutOptions

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Couchbase bucket / scope / collection mapping (PRD §7)
BUCKET = "banking-core"

COLLECTION_MAP: dict[str, tuple[str, str]] = {
    # (scope, collection)
    "customers": ("customers", "profiles"),
    "households": ("customers", "households"),
    "customer_signals": ("customers", "preferences"),
    "transactions": ("transactions", "ledger_events"),
    "devices": ("transactions", "devices"),
    "fraud_alerts": ("agents", "recommendations"),
    "fraud_rings": ("agents", "case_context"),
    "loan_applications": ("loans", "applications"),
    "loan_reviews": ("loans", "reviews"),
    "loan_exceptions": ("loans", "policy_refs"),
    "interactions": ("interactions", "transcripts"),
    "interaction_analyses": ("interactions", "analysis"),
    "branch_kpis": ("branches", "kpis"),
    "branch_alerts": ("branches", "alerts"),
    "branch_insights": ("branches", "alerts"),
    "cases": ("agents", "case_context"),
    "advice_drafts": ("agents", "recommendations"),
    "audit_events": ("audit", "events"),
    "agent_traces": ("audit", "events"),
    "agent_sessions": ("agents", "session_state"),
}


class CouchbaseClient:
    """
    Manages the Couchbase cluster connection.

    Call `await client.connect()` once at application startup.
    All repositories receive this client via dependency injection.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cluster: Cluster | None = None
        self._connected = False

    async def connect(self) -> None:
        if self._connected:
            return
        try:
            auth = PasswordAuthenticator(
                self._settings.couchbase_username,
                self._settings.couchbase_password,
            )
            timeout_opts = ClusterTimeoutOptions(
                connect_timeout=10.0,
                kv_timeout=5.0,
                query_timeout=30.0,
            )
            opts = ClusterOptions(auth, timeout_options=timeout_opts)
            # The SDK connect is synchronous; run it in executor to not block event loop
            loop = asyncio.get_event_loop()
            self._cluster = await loop.run_in_executor(
                None,
                lambda: Cluster(self._settings.couchbase_connection_string, opts),
            )
            self._connected = True
            logger.info(
                "Couchbase connection established",
                extra={"host": self._settings.couchbase_connection_string},
            )
        except CouchbaseException as exc:
            logger.error("Couchbase connection failed: %s", exc)
            raise

    async def close(self) -> None:
        if self._cluster and self._connected:
            self._cluster.close()
            self._connected = False

    def get_collection(self, logical_name: str) -> Collection:
        """Return the Couchbase Collection for a logical collection name."""
        if not self._connected or self._cluster is None:
            raise RuntimeError("CouchbaseClient is not connected. Call await connect() first.")
        scope_name, collection_name = COLLECTION_MAP[logical_name]
        bucket = self._cluster.bucket(self._settings.couchbase_bucket)
        return bucket.scope(scope_name).collection(collection_name)

    def cluster(self) -> Cluster:
        if self._cluster is None:
            raise RuntimeError("CouchbaseClient is not connected.")
        return self._cluster
