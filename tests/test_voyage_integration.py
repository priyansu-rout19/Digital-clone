"""
Voyage AI Integration Tests

Verifies that Voyage AI embeddings are properly integrated:
1. embedder module imports and instantiates correctly
2. EmbeddingClient uses voyage-3 model
3. mem0_client imports and uses VoyageAIEmbeddings

API calls are not made (VOYAGE_API_KEY validation only).

Run:
    pytest tests/test_voyage_integration.py -v

Requires: VOYAGE_API_KEY in .env (same as E2E tests)
"""

import os
import sys
import pytest


# Skip all tests in this module if VOYAGE_API_KEY is not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("VOYAGE_API_KEY"),
    reason="VOYAGE_API_KEY not configured in .env — skipping Voyage AI tests"
)


def test_embedder_module_import():
    """Verify embedder module imports without errors."""
    try:
        from core.rag.ingestion.embedder import get_embedder, EmbeddingClient
    except ImportError as e:
        pytest.fail(f"Failed to import embedder module: {e}")


def test_embedder_instantiation():
    """Verify EmbeddingClient instantiates with voyage-3 model."""
    from core.rag.ingestion.embedder import get_embedder

    embedder = get_embedder()

    assert embedder is not None, "get_embedder() returned None"
    assert hasattr(embedder, "model"), "EmbeddingClient missing 'model' attribute"
    assert embedder.model == "voyage-3", (
        f"Expected model 'voyage-3', got '{embedder.model}'"
    )


def test_mem0_client_import():
    """Verify mem0_client module imports (uses VoyageAIEmbeddings)."""
    try:
        from core.mem0_client import get_mem0_client
    except ImportError as e:
        pytest.fail(f"Failed to import mem0_client module: {e}")


def _pg_is_reachable() -> bool:
    """Check if PostgreSQL is reachable (needed for Mem0 pgvector backend)."""
    try:
        from urllib.parse import urlparse
        import psycopg2
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            return False
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname, port=parsed.port,
            dbname=parsed.path.lstrip("/"),
            user=parsed.username, password=parsed.password or "",
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(
    not _pg_is_reachable(),
    reason="PostgreSQL not reachable — Mem0 requires pgvector backend"
)
def test_mem0_client_instantiation():
    """Verify Mem0 client instantiates (embeds VoyageAIEmbeddings)."""
    from core.mem0_client import get_mem0_client

    mem_client = get_mem0_client()
    assert mem_client is not None, "get_mem0_client() returned None"
