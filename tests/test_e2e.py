"""
E2E Integration Tests — Digital Clone Engine

Tests the full 19-node LangGraph pipeline for both clone profiles.
LLM calls (query_analysis, in_persona_generator, confidence_scorer) use real Groq API.
DB-dependent nodes (vector_search, Mem0) are mocked with canned data.

Run:
    pytest tests/test_e2e.py -v
    pytest tests/test_e2e.py -v -s      # show stdout (review_queue prints)
    pytest tests/test_e2e.py::test_citation_verifier_direct -v   # fast, no LLM

Requires: GROQ_API_KEY in .env (already configured). No DATABASE_URL needed.
"""

import copy
import pytest
from unittest.mock import patch, MagicMock

from core.models.clone_profile import paragpt_profile, sacred_archive_profile
from core.langgraph.conversation_flow import build_graph
from core.langgraph.nodes.generation_nodes import citation_verifier


# ---------------------------------------------------------------------------
# Sample Data
# ---------------------------------------------------------------------------

SAMPLE_PASSAGES = [
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
    {
        "doc_id": "doc-002",
        "chunk_id": "doc-002_0001",
        "passage": (
            "The future belongs to agile civilizations that embrace networks over territories. "
            "Supply chain sovereignty and data sovereignty are now geopolitical imperatives."
        ),
        "source_type": "lecture",
        "access_tier": "public",
        "date": "2023",
    },
]

VALID_INTENT_CLASSES = {"factual", "synthesis", "opinion", "temporal", "exploratory"}

BASE_STATE = {
    "query_text": "What is the future of global connectivity?",
    "sub_queries": [],
    "intent_class": "",
    "access_tier": "public",
    "token_budget": 2000,
    "clone_id": "test-clone-uuid-001",
    "user_id": "test-user-uuid-001",
    "retrieved_passages": [],
    "provenance_graph_results": [],
    "retrieval_confidence": 0.0,
    "retry_count": 0,
    "assembled_context": "",
    "user_memory": "",
    "raw_response": "",
    "verified_response": "",
    "final_confidence": 0.0,
    "cited_sources": [],
    "silence_triggered": False,
    "voice_chunks": [],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_retrieval():
    """
    Patches vector_search.search → (SAMPLE_PASSAGES, 0.85).
    Confidence 0.85 is above ParaGPT threshold (0.80), so no CRAG loop fires.
    NOT suitable for Sacred Archive (threshold 0.95) — use inline patch for that test.
    """
    with patch("core.rag.retrieval.vector_search.search") as mock:
        mock.return_value = (SAMPLE_PASSAGES, 0.85)
        yield mock


@pytest.fixture
def mock_memory():
    """
    Patches get_mem0_client → MagicMock mimicking the Mem0 Memory interface.
    .search() returns the Mem0 result format: {"results": []}.
    .add() returns None (side-effect write).
    """
    with patch("core.mem0_client.get_mem0_client") as mock:
        mem_client = MagicMock()
        mem_client.search.return_value = {"results": []}
        mem_client.add.return_value = None
        mock.return_value = mem_client
        yield mock


# ---------------------------------------------------------------------------
# Test 1: ParaGPT full pipeline
# ---------------------------------------------------------------------------

def test_paragpt_full_flow(mock_retrieval, mock_memory):
    """
    Happy path for ParaGPT: query → retrieve → memory → generate → verify → stream.
    Exercises all 12 nodes on the ParaGPT path including memory_retrieval,
    memory_writer, and voice_pipeline (stub).
    """
    profile = paragpt_profile()
    graph = build_graph(profile)

    result = graph.invoke(copy.deepcopy(BASE_STATE))

    assert result["intent_class"] in VALID_INTENT_CLASSES, (
        f"intent_class '{result['intent_class']}' not in valid set"
    )
    assert result["raw_response"], "in_persona_generator must produce a response"
    assert result["verified_response"], "citation_verifier must set verified_response"
    assert isinstance(result["cited_sources"], list), "cited_sources must be a list"
    assert 0.0 <= result["final_confidence"] <= 1.0, (
        f"final_confidence {result['final_confidence']} out of [0.0, 1.0]"
    )
    assert isinstance(result["voice_chunks"], list), "stream_to_user must populate voice_chunks"
    assert isinstance(result["user_memory"], str), "memory_retrieval must set user_memory string"


# ---------------------------------------------------------------------------
# Test 2: Sacred Archive full pipeline
# ---------------------------------------------------------------------------

def test_sacred_archive_full_flow():
    """
    Happy path for Sacred Archive: mirror_only generation, no memory,
    always routes to review_queue_writer (review_required=True).

    Uses inline patch returning confidence 0.96 (above Sacred Archive threshold 0.95)
    to prevent the CRAG retry loop from firing.
    """
    with patch("core.rag.retrieval.vector_search.search") as mock_search:
        mock_search.return_value = (SAMPLE_PASSAGES, 0.96)

        profile = sacred_archive_profile()
        graph = build_graph(profile)

        state = copy.deepcopy(BASE_STATE)
        state["access_tier"] = "devotee"

        result = graph.invoke(state)

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
# Test 3: CRAG retry loop
# ---------------------------------------------------------------------------

def test_crag_retry_loop(mock_memory):
    """
    Validates the CRAG retry mechanism. Forces two low-confidence retrievals
    (triggering query_reformulator each time) then a high-confidence retrieval.
    Asserts retry_count >= 1 to prove the reformulator ran.
    """
    with patch("core.rag.retrieval.vector_search.search") as mock_search:
        mock_search.side_effect = [
            (SAMPLE_PASSAGES, 0.3),   # Below ParaGPT threshold 0.80 → retry
            (SAMPLE_PASSAGES, 0.3),   # Still below → retry again
            (SAMPLE_PASSAGES, 0.9),   # Above threshold → proceed
        ]

        profile = paragpt_profile()
        graph = build_graph(profile)
        result = graph.invoke(copy.deepcopy(BASE_STATE))

    assert result["retry_count"] >= 1, (
        f"CRAG loop should have fired at least once, got retry_count={result['retry_count']}"
    )
    assert result["raw_response"], "pipeline must still produce response after CRAG retries"


# ---------------------------------------------------------------------------
# Test 4: citation_verifier direct unit test
# ---------------------------------------------------------------------------

def test_citation_verifier_direct():
    """
    Tests citation_verifier in isolation — no graph, no LLM, no mocks.
    Pure Python node: regex parse [N] markers, cross-ref against passages.
    Verifies that [1] resolves correctly and [5] is caught as hallucination
    (only 1 passage provided, so index 5 is out of range).
    """
    passages = [SAMPLE_PASSAGES[0]]   # 1 passage only

    state = {
        **BASE_STATE,
        "retrieved_passages": passages,
        "raw_response": "Connectivity shapes global order [1]. See also [5] for context.",
    }

    result = citation_verifier(state)

    assert len(result["cited_sources"]) == 1, (
        f"[1] should resolve, [5] should be caught as hallucination. "
        f"Got {len(result['cited_sources'])} cited sources."
    )
    assert result["cited_sources"][0]["doc_id"] == "doc-001"
    assert result["verified_response"] == state["raw_response"]
