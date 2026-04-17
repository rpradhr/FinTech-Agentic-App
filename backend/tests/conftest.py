"""
Shared test fixtures.

All tests run against the in-memory adapter (APP_ENV=test).
No Couchbase or AI credentials are needed.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Force test environment before any app imports
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")

from app.api.auth import create_dev_token
from app.core.config import get_settings
from app.core.container import Container, set_container
from app.infrastructure.persistence.memory import InMemoryStore
from app.main import create_app


@pytest.fixture(scope="session")
def settings():
    get_settings.cache_clear()
    return get_settings()


@pytest_asyncio.fixture
async def container(settings):
    """Fresh in-memory container for each test."""
    c = Container(settings)
    await c.connect()
    set_container(c)
    yield c
    await c.close()


@pytest_asyncio.fixture
async def async_client(container):
    """Async HTTP client wired to the test app with a fraud_analyst token."""
    app = create_app()
    token = create_dev_token("test-analyst", ["fraud_analyst", "underwriter", "cx_lead",
                                               "financial_advisor", "branch_manager",
                                               "compliance_reviewer", "admin"])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client
