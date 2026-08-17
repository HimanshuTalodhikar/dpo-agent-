"""
Pytest configuration and fixtures for all test suites.
"""

import pytest
import pytest_asyncio

from src.services.zep_graphrag import (
    get_graphrag_service,
    get_sync_graphrag_service,
)


# ── Graphiti + Neptune Fixtures ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def graph_name() -> str:
    """Graph name used in tests (uses env var or default)."""
    from src.services.zep_graphrag import GRAPH_NAME
    return GRAPH_NAME


@pytest.fixture(scope="session")
def service():
    """Create a sync graph service for tests."""
    svc = get_sync_graphrag_service()
    yield svc
    svc.close()


@pytest.fixture(scope="session")
def async_service():
    """Create an async graph service for async tests."""
    svc = get_graphrag_service(sync=False)
    yield svc
    import asyncio
    asyncio.run(svc.close())


@pytest.fixture(scope="session")
def queries() -> list[str]:
    return [
        "What are the cybersecurity requirements for government systems?",
        "What is the procurement target for MSEs?",
        "How to file an RTI application?",
        "What is the school structure under NEP 2020?",
        "Digital India connectivity requirements for Gram Panchayats",
    ]
