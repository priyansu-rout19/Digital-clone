"""
Tests for query analysis — pre-filter, intent classification, token budgets.

Covers: core/langgraph/nodes/query_analysis_node.py
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from core.langgraph.nodes.query_analysis_node import (
    _prefilter,
    _persona_result,
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
# Pre-filter (single-word greetings) — from test_session43
# ===========================================================================

class TestPrefilter:
    """Pre-LLM fast path catches single-word greetings only."""

    GREETING_QUERIES = [
        "hi",
        "hello",
        "hii",
        "hey",
        "namaste",
        "thanks",
        "bye",
        "yo",
    ]

    @pytest.mark.parametrize("query", GREETING_QUERIES, ids=GREETING_QUERIES)
    def test_greetings_caught(self, query):
        result = _prefilter(query)
        assert result is not None
        assert result["intent_class"] == "persona"
        assert result["sub_queries"] == []
        assert result["token_budget"] == 0

    SHOULD_DEFER_QUERIES = [
        "hii i am Priyansu from india",
        "Hi, what is ASEAN?",
        "How does infrastructure shape global power?",
        "What role does urbanization play in climate?",
        "Explain connectivity frameworks",
        "Tell me about supply chain resilience",
        "What is my name?",
        "Who are you?",
        "Where am I from?",
        "Do you remember me?",
    ]

    @pytest.mark.parametrize("query", SHOULD_DEFER_QUERIES,
                             ids=[q[:25] for q in SHOULD_DEFER_QUERIES])
    def test_multi_word_queries_defer_to_llm(self, query):
        """Multi-word queries (including intros, self-ref, identity) all go to LLM now."""
        result = _prefilter(query)
        assert result is None

    def test_prefilter_skips_llm(self):
        """When pre-filter fires, query_analysis returns immediately without calling LLM."""
        state = {"query_text": "hello", "conversation_history": ""}
        with patch("core.langgraph.nodes.query_analysis_node.get_llm") as mock_llm:
            result = query_analysis(state)
            mock_llm.assert_not_called()
        assert result["intent_class"] == "persona"
        assert result["retry_count"] == 0

    def test_empty_query_persona(self):
        """Empty string caught by pre-filter as persona."""
        result = _prefilter("")
        assert result is not None
        assert result["intent_class"] == "persona"


# ===========================================================================
# Self-referential queries via LLM — from test_session42
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
# Greeting fallback — from test_session42
# ===========================================================================

class TestGreetingFallback:
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
# Negative tests — non-persona queries — from test_session42
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
# Graph routing — persona skips retrieval — from test_session42
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
# Token budget — from test_session16
# ===========================================================================

class TestTokenBudget:

    def test_default_on_empty_query(self):
        """Empty query should get DEFAULT_TOKEN_BUDGET."""
        from core.langgraph.nodes.query_analysis_node import query_analysis, DEFAULT_TOKEN_BUDGET

        state = {"query_text": ""}
        result = query_analysis(state)
        assert result["token_budget"] == DEFAULT_TOKEN_BUDGET

    def test_llm_decides_budget(self):
        """LLM should return token_budget in its JSON response."""
        from core.langgraph.nodes.query_analysis_node import query_analysis

        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "intent": "retrieval",
            "sub_queries": ["query 1", "query 2"],
            "token_budget": 3000,
        })

        with patch("core.langgraph.nodes.query_analysis_node.get_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            state = {"query_text": "How does connectivity relate to human evolution?"}
            result = query_analysis(state)

            assert result["token_budget"] == 3000
            assert result["intent_class"] == "retrieval"

    def test_budget_clamped_to_range(self):
        """Token budget should be clamped to [1000, 4000]."""
        from core.langgraph.nodes.query_analysis_node import query_analysis

        # Test upper clamp
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "intent": "exploratory",
            "sub_queries": ["test"],
            "token_budget": 99999,
        })

        with patch("core.langgraph.nodes.query_analysis_node.get_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = query_analysis({"query_text": "test"})
            assert result["token_budget"] == 4000  # clamped

    def test_fallback_on_parse_error(self):
        """Bad JSON from LLM should fall back to DEFAULT_TOKEN_BUDGET."""
        from core.langgraph.nodes.query_analysis_node import query_analysis, DEFAULT_TOKEN_BUDGET

        mock_response = MagicMock()
        mock_response.content = "not valid json at all"

        with patch("core.langgraph.nodes.query_analysis_node.get_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response
            result = query_analysis({"query_text": "test query"})
            assert result["token_budget"] == DEFAULT_TOKEN_BUDGET
