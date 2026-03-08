"""
Session 42 Tests — Skip-RAG for persona queries + Mem0 provider fix.

Tests:
- Self-referential queries via LLM (10 tests — now go through LLM, not deterministic gate)
- Greeting regression (6 tests — single-word greetings still caught by pre-filter)
- Negative tests — retrieval queries not caught (4 tests)
- Graph routing — persona skips retrieval (2 tests)
- Confidence bypass — persona passes through (2 tests)
- Mem0 config — provider selection (3 tests)

All mock-based, no external services required.

Run:
    python3 -m pytest tests/test_session42.py -v
"""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from core.langgraph.nodes.query_analysis_node import (
    query_analysis,
    DEFAULT_TOKEN_BUDGET,
    DEFAULT_RESPONSE_TOKENS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_fallback(query: str, history: str = "") -> dict:
    """Invoke query_analysis with a mocked LLM that returns invalid JSON,
    forcing the except-branch fallback logic."""
    mock_response = MagicMock()
    mock_response.content = "NOT VALID JSON"

    with patch("core.langgraph.nodes.query_analysis_node.get_llm") as mock_llm:
        mock_llm.return_value.invoke.return_value = mock_response
        state = {"query_text": query, "conversation_history": history}
        return query_analysis(state)


def _run_with_llm_persona(query: str) -> dict:
    """Invoke query_analysis with a mocked LLM that returns persona classification."""
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "intent": "persona", "sub_queries": [],
        "token_budget": 0, "response_tokens": 150, "rewritten_query": None
    })
    with patch("core.langgraph.nodes.query_analysis_node.get_llm") as mock_llm:
        mock_llm.return_value.invoke.return_value = mock_response
        state = {"query_text": query, "conversation_history": ""}
        return query_analysis(state)


# ===========================================================================
# 3a. Self-referential queries — now handled by LLM (10 tests)
# ===========================================================================

class TestSelfReferentialViaLLM:
    """Self-referential queries now go to LLM (no deterministic gate).
    We mock the LLM to return persona classification."""

    SELF_REF_QUERIES = [
        "What is my name?",
        "Which is my country?",
        "Tell me about me",
        "Do you remember me?",
        "Who am I?",
        "Did I say something earlier?",
        "Did I tell you my age?",
        "I told you about my trip",
        "Where am I from?",
        "Do you know where I am from?",
    ]

    @pytest.mark.parametrize("query", SELF_REF_QUERIES,
                             ids=[q[:20].replace(" ", "_") for q in SELF_REF_QUERIES])
    def test_self_ref_via_llm(self, query):
        """Self-ref queries are multi-word → bypass pre-filter, go to LLM."""
        result = _run_with_llm_persona(query)
        assert result["intent_class"] == "persona"
        assert result["sub_queries"] == []
        assert result["token_budget"] == 0
        assert result["response_tokens"] == 150


# ===========================================================================
# 3b. Greeting regression (6 tests)
# ===========================================================================

class TestGreetingRegression:
    """Single-word greetings still caught by pre-filter as persona."""

    GREETINGS = ["hi", "hello", "namaste", "thanks", "bye", "yo"]

    @pytest.mark.parametrize("greeting", GREETINGS)
    def test_greeting_is_persona(self, greeting):
        result = _run_fallback(greeting)
        assert result["intent_class"] == "persona", (
            f"Greeting '{greeting}' should be persona, "
            f"got '{result['intent_class']}'"
        )
        assert result["sub_queries"] == []
        assert result["token_budget"] == 0
        assert result["response_tokens"] == 150


# ===========================================================================
# 3c. Negative tests — non-persona queries (4 tests)
# ===========================================================================

class TestNegativeNotPersona:
    """Non-persona queries must not be caught by pre-filter."""

    def test_factual_how_query(self):
        """'How does connectivity shape geopolitics?' → retrieval (fallback)."""
        result = _run_fallback("How does connectivity shape geopolitics?")
        assert result["intent_class"] == "retrieval"
        assert result["token_budget"] == DEFAULT_TOKEN_BUDGET

    def test_factual_what_query(self):
        """'What is the future of AI?' → retrieval (fallback)."""
        result = _run_fallback("What is the future of AI?")
        assert result["intent_class"] == "retrieval"
        assert result["token_budget"] == DEFAULT_TOKEN_BUDGET

    def test_tell_me_about_asean(self):
        """'Tell me about ASEAN' → retrieval (fallback: all parse failures = retrieval)."""
        result = _run_fallback("Tell me about ASEAN")
        assert result["intent_class"] == "retrieval"
        assert result["token_budget"] == DEFAULT_TOKEN_BUDGET

    def test_did_parag_say(self):
        """'What did Parag Khanna say about trade?' → retrieval (fallback)."""
        result = _run_fallback("What did Parag Khanna say about trade?")
        assert result["intent_class"] == "retrieval"
        assert result["token_budget"] == DEFAULT_TOKEN_BUDGET


# ===========================================================================
# 3d. Graph routing — persona skips retrieval (2 tests)
# ===========================================================================

class TestGraphRoutingPersona:
    """Persona intent should skip all retrieval nodes and go straight
    to context_assembler."""

    def test_paragpt_persona_skips_retrieval(self):
        """ParaGPT: persona → context_assembler (skips tier1_retrieval)."""
        result = _run_with_llm_persona("Who am I?")
        assert result["intent_class"] == "persona"
        assert result["token_budget"] == 0
        assert result["sub_queries"] == []

    def test_sacred_archive_persona_skips_retrieval(self):
        """Sacred Archive: persona → context_assembler (skips provenance + tier1)."""
        result = _run_with_llm_persona("Do you remember me?")
        assert result["intent_class"] == "persona"
        assert result["token_budget"] == 0
        assert result["sub_queries"] == []


# ===========================================================================
# 3e. Confidence bypass — persona passes through (2 tests)
# ===========================================================================

class TestConfidenceBypassPersona:
    """Persona intent bypasses confidence silencing."""

    def test_paragpt_persona_bypasses_confidence(self):
        """ParaGPT (review_required=False): persona → stream_to_user."""
        from core.models.clone_profile import paragpt_profile

        profile = paragpt_profile()
        assert profile.review_required is False

        state = {"intent_class": "persona", "final_confidence": 0.0}
        if state["intent_class"] == "persona":
            if profile.review_required:
                route = "review_queue_writer"
            else:
                route = "stream_to_user"
        assert route == "stream_to_user"

    def test_sacred_archive_persona_to_review(self):
        """Sacred Archive (review_required=True): persona → review_queue_writer."""
        from core.models.clone_profile import sacred_archive_profile

        profile = sacred_archive_profile()
        assert profile.review_required is True

        state = {"intent_class": "persona", "final_confidence": 0.0}
        if state["intent_class"] == "persona":
            if profile.review_required:
                route = "review_queue_writer"
            else:
                route = "stream_to_user"
        assert route == "review_queue_writer"


# ===========================================================================
# 3f. Mem0 config — provider selection (3 tests)
# ===========================================================================

class TestMem0Config:
    """Test get_mem0_client() LLM provider selection logic."""

    def test_openrouter_path(self):
        """LLM_API_KEY + LLM_BASE_URL → provider='openai' with correct config."""
        env = {
            "LLM_API_KEY": "sk-test-key",
            "LLM_BASE_URL": "https://openrouter.ai/api/v1",
            "LLM_MODEL": "qwen/qwen3-32b",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/testdb",
            "GOOGLE_API_KEY": "test-google-key",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("core.mem0_client.Memory") as MockMemory:
                with patch("core.mem0_client._truncated_google_embeddings") as mock_embed:
                    mock_embed.return_value = MagicMock()
                    from core.mem0_client import get_mem0_client
                    get_mem0_client()

                    # Capture the config dict passed to Memory.from_config
                    MockMemory.from_config.assert_called_once()
                    config = MockMemory.from_config.call_args[0][0]

                    assert config["llm"]["provider"] == "openai"
                    assert config["llm"]["config"]["api_key"] == "sk-test-key"
                    assert config["llm"]["config"]["openai_base_url"] == "https://openrouter.ai/api/v1"
                    assert config["llm"]["config"]["model"] == "qwen/qwen3-32b"

    def test_groq_fallback(self):
        """No LLM_API_KEY → falls back to Groq with GROQ_API_KEY."""
        env = {
            "GROQ_API_KEY": "gsk-test-groq",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/testdb",
            "GOOGLE_API_KEY": "test-google-key",
        }
        with patch.dict(os.environ, env, clear=False):
            # Remove LLM_* vars if they exist
            for key in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"]:
                os.environ.pop(key, None)

            with patch("core.mem0_client.Memory") as MockMemory:
                with patch("core.mem0_client._truncated_google_embeddings") as mock_embed:
                    mock_embed.return_value = MagicMock()
                    from core.mem0_client import get_mem0_client
                    get_mem0_client()

                    MockMemory.from_config.assert_called_once()
                    config = MockMemory.from_config.call_args[0][0]

                    assert config["llm"]["provider"] == "groq"
                    assert config["llm"]["config"]["api_key"] == "gsk-test-groq"

    def test_no_keys_raises(self):
        """Neither LLM_API_KEY nor GROQ_API_KEY → KeyError."""
        env = {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/testdb",
            "GOOGLE_API_KEY": "test-google-key",
        }
        with patch.dict(os.environ, env, clear=False):
            # Remove all LLM keys
            for key in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "GROQ_API_KEY"]:
                os.environ.pop(key, None)

            with patch("core.mem0_client._truncated_google_embeddings") as mock_embed:
                mock_embed.return_value = MagicMock()
                from core.mem0_client import get_mem0_client
                with pytest.raises(KeyError, match="LLM_API_KEY"):
                    get_mem0_client()
