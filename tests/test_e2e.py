"""
E2E Integration Tests — Digital Clone Engine

Tests the full 19-node LangGraph pipeline for both clone profiles.
ALL nodes use REAL services: Groq LLM, Google Gemini embeddings, Mem0 memory,
and PostgreSQL database. No mocks.

Run:
    pytest tests/test_e2e.py -v
    pytest tests/test_e2e.py -v -s      # show stdout (review_queue prints)
    pytest tests/test_e2e.py::test_citation_verifier_direct -v   # fast, no LLM

Requires: DATABASE_URL, GROQ_API_KEY, and GOOGLE_API_KEY in .env.
"""

import os
import pytest

from core.models.clone_profile import paragpt_profile, sacred_archive_profile
from core.langgraph.conversation_flow import build_graph
from core.langgraph.nodes.generation_nodes import citation_verifier


# ---------------------------------------------------------------------------
# Skip entire module if required env vars are missing
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL") or not os.environ.get("GROQ_API_KEY") or not os.environ.get("GOOGLE_API_KEY"),
    reason="Integration tests require DATABASE_URL, GROQ_API_KEY, and GOOGLE_API_KEY",
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_INTENT_CLASSES = {"factual", "synthesis", "opinion", "temporal", "exploratory"}

# Sample data for citation_verifier unit test only
CITATION_TEST_PASSAGES = [
    {
        "doc_id": "doc-001",
        "chunk_id": "doc-001_0000",
        "passage": (
            "Connectivity is the defining mega-trend of the 21st century. "
            "Nations that control infrastructure — digital, physical, and financial — "
            "will shape global order for decades to come."
        ),
        "source_type": "book",
        "access_tier": "public",
        "date": "2016",
    },
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_state(query: str, clone_id: str, user_id: str = "test-user-001",
               access_tier: str = "public") -> dict:
    """Build a fresh ConversationState dict for a given query and clone."""
    return {
        "query_text": query,
        "sub_queries": [],
        "intent_class": "",
        "access_tier": access_tier,
        "token_budget": 2000,
        "clone_id": clone_id,
        "user_id": user_id,
        "retrieved_passages": [],
        "provenance_graph_results": [],
        "retrieval_confidence": 0.0,
        "retry_count": 0,
        "assembled_context": "",
        "user_memory": "",
        "conversation_history": "",
        "raw_response": "",
        "verified_response": "",
        "final_confidence": 0.0,
        "cited_sources": [],
        "silence_triggered": False,
        "voice_chunks": [],
        "audio_base64": "",
        "audio_format": "",
    }


# ---------------------------------------------------------------------------
# Test 1: ParaGPT full pipeline (real DB, real vector search, real Mem0)
# ---------------------------------------------------------------------------

def test_paragpt_full_flow(paragpt_clone_id):
    """
    Happy path for ParaGPT: query -> retrieve -> memory -> generate -> verify -> stream.
    Uses REAL vector_search (pgvector), REAL Mem0, and REAL Groq LLM.
    No mocks — the database must be seeded with sample documents.
    """
    profile = paragpt_profile()
    graph = build_graph(profile)

    state = make_state(
        query="What is the future of global connectivity?",
        clone_id=paragpt_clone_id,
    )
    result = graph.invoke(state)

    # Intent classification
    assert result["intent_class"] in VALID_INTENT_CLASSES, (
        f"intent_class '{result['intent_class']}' not in valid set"
    )

    # Real retrieval produced passages
    assert len(result["retrieved_passages"]) > 0, (
        "vector_search must find passages from ingested ParaGPT documents"
    )
    assert result["retrieval_confidence"] > 0.0, (
        "retrieval_confidence must be non-zero with real vector search"
    )

    # Generation and verification
    assert result["raw_response"], "in_persona_generator must produce a response"
    assert result["verified_response"], "citation_verifier must set verified_response"
    assert isinstance(result["cited_sources"], list), "cited_sources must be a list"
    assert 0.0 <= result["final_confidence"] <= 1.0, (
        f"final_confidence {result['final_confidence']} out of [0.0, 1.0]"
    )

    # Streaming and memory
    assert isinstance(result["voice_chunks"], list), "stream_to_user must populate voice_chunks"
    assert isinstance(result["user_memory"], str), "memory_retrieval must set user_memory string"


# ---------------------------------------------------------------------------
# Test 2: Sacred Archive full pipeline (real DB, real vector search, no memory)
# ---------------------------------------------------------------------------

def test_sacred_archive_full_flow(sacred_clone_id):
    """
    Happy path for Sacred Archive: mirror_only generation, no memory,
    always routes to review_queue_writer (review_required=True).
    Uses REAL vector_search, REAL Groq LLM. No mocks.
    """
    profile = sacred_archive_profile()
    graph = build_graph(profile)

    state = make_state(
        query="What is the nature of compassion?",
        clone_id=sacred_clone_id,
        access_tier="devotee",
    )
    result = graph.invoke(state)

    # Real retrieval produced passages
    assert len(result["retrieved_passages"]) > 0, (
        "vector_search must find passages from ingested Sacred Archive documents"
    )
    assert result["retrieval_confidence"] > 0.0, (
        "retrieval_confidence must be non-zero with real vector search"
    )

    # Generation
    assert result["raw_response"], "in_persona_generator must produce a response"
    assert result["user_memory"] == "", (
        "Sacred Archive has user_memory_enabled=False — user_memory must stay empty"
    )
    assert isinstance(result["cited_sources"], list), "cited_sources must be a list"
    assert 0.0 <= result["final_confidence"] <= 1.0, (
        f"final_confidence {result['final_confidence']} out of [0.0, 1.0]"
    )
    assert result["query_text"] == state["query_text"], "graph must complete and preserve state"


# ---------------------------------------------------------------------------
# Test 3: CRAG retry loop (nonsensical query triggers low confidence)
# ---------------------------------------------------------------------------

def test_crag_retry_loop(paragpt_clone_id):
    """
    Validates the CRAG retry mechanism using a NONSENSICAL query.
    Real vector_search returns low-confidence results for gibberish,
    which falls below ParaGPT CRAG retry threshold (0.30, i.e. DB threshold 0.60 * 0.5) and triggers the
    query_reformulator -> re-retrieval loop.

    Asserts retry_count >= 1 to prove the reformulator ran.
    """
    profile = paragpt_profile()
    graph = build_graph(profile)

    state = make_state(
        query="xyz123 quantum flamingo zebra paradox nonsensical",
        clone_id=paragpt_clone_id,
    )
    result = graph.invoke(state)

    assert result["retry_count"] >= 1, (
        f"CRAG loop should have fired at least once for nonsensical query, "
        f"got retry_count={result['retry_count']}"
    )
    assert result["raw_response"], "pipeline must still produce response after CRAG retries"


# ---------------------------------------------------------------------------
# Test 4: citation_verifier direct unit test (no DB, no LLM, no mocks)
# ---------------------------------------------------------------------------

def test_citation_verifier_direct():
    """
    Tests citation_verifier in isolation — no graph, no LLM, no mocks.
    Pure Python node: regex parse [N] markers, cross-ref against passages.
    Verifies that [1] resolves correctly and [5] is caught as hallucination
    (only 1 passage provided, so index 5 is out of range).
    """
    passages = [CITATION_TEST_PASSAGES[0]]   # 1 passage only

    state = {
        **make_state(query="What is the future of global connectivity?", clone_id="test-clone-uuid-001"),
        "retrieved_passages": passages,
        "raw_response": "Connectivity shapes global order [1]. See also [5] for context.",
    }

    result = citation_verifier(state)

    assert len(result["cited_sources"]) == 1, (
        f"[1] should resolve, [5] should be caught as hallucination. "
        f"Got {len(result['cited_sources'])} cited sources."
    )
    # Frontend-facing field names (remapped from source_type/passage)
    assert result["cited_sources"][0]["source"] == "book"
    assert "Connectivity" in result["cited_sources"][0]["chunk_text"]
    # Internal fields still preserved
    assert result["cited_sources"][0]["doc_id"] == "doc-001"
    # [N] markers stripped from verified_response
    assert "[1]" not in result["verified_response"]
    assert "[5]" not in result["verified_response"]
    assert "Connectivity shapes global order" in result["verified_response"]
