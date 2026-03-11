"""
Tests for generation nodes — confidence scoring, context bleed, Mem0 injection, guardrails.

Covers: core/langgraph/nodes/generation_nodes.py
"""

import pytest
from unittest.mock import patch, MagicMock

from core.langgraph.nodes.generation_nodes import (
    make_in_persona_generator,
    confidence_scorer,
)
from core.models.clone_profile import paragpt_profile, sacred_archive_profile


# ===========================================================================
# Confidence scoring — from test_session43
# ===========================================================================

class TestConfidenceScoring:
    """History excluded from grounding; multi-turn bonus conditional on citations."""

    def test_no_history_in_grounding(self):
        """History should NOT inflate grounding score."""
        state_no_history = {
            "verified_response": "Infrastructure drives connectivity across regions",
            "intent_class": "factual",
            "retrieval_confidence": 0.5,
            "retrieved_passages": [{"passage": "Infrastructure connectivity"}],
            "cited_sources": [{"source": "book"}],
            "assembled_context": "Infrastructure connectivity across regions",
            "conversation_history": "",
        }
        score_no_hist = confidence_scorer(state_no_history)["final_confidence"]

        state_with_history = {
            **state_no_history,
            "conversation_history": "User: What about infrastructure?\nAssistant: Infrastructure drives connectivity across regions",
        }
        score_with_hist = confidence_scorer(state_with_history)["final_confidence"]

        # With history + citations, only a 0.05 bonus — NOT inflated grounding
        assert score_with_hist - score_no_hist == pytest.approx(0.05, abs=0.001)

    def test_no_bonus_without_citations(self):
        """Multi-turn bonus should NOT apply when there are no citations."""
        state = {
            "verified_response": "Hello! Nice to meet you.",
            "intent_class": "factual",  # Not conversational, to test the scoring path
            "retrieval_confidence": 0.0,
            "retrieved_passages": [],
            "cited_sources": [],
            "assembled_context": "",
            "conversation_history": "User: hi\nAssistant: Hello!",
        }
        score = confidence_scorer(state)["final_confidence"]
        # No passages, no citations, no context → score should be 0.0
        assert score == 0.0

    def test_persona_bypass(self):
        """Persona intent returns 1.0 regardless."""
        state = {
            "verified_response": "Hey! Great to meet you.",
            "intent_class": "persona",
        }
        assert confidence_scorer(state)["final_confidence"] == 1.0


# ===========================================================================
# Context bleed fix — from test_session43
# ===========================================================================

class TestContextBleed:
    """History separated from context via multi-message structure."""

    def test_history_in_separate_message(self):
        """When history exists, LLM receives it as a separate user+assistant pair."""
        profile = paragpt_profile()
        gen_fn = make_in_persona_generator(profile)

        state = {
            "query_text": "How does infrastructure shape power?",
            "assembled_context": "[1] Infrastructure drives connectivity.",
            "user_memory": "",
            "conversation_history": "User: hi\nAssistant: Hello!",
            "intent_class": "factual",
            "response_tokens": 200,
        }

        with patch("core.langgraph.nodes.generation_nodes.get_llm") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "Infrastructure shapes power [1]."
            mock_llm.return_value.invoke.return_value = mock_response

            gen_fn(state)

            # Check the messages passed to LLM
            call_args = mock_llm.return_value.invoke.call_args[0][0]
            assert len(call_args) == 4  # system + history_user + history_assistant + current_user
            assert call_args[0]["role"] == "system"
            assert call_args[1]["role"] == "user"
            assert "do NOT respond to these" in call_args[1]["content"]
            assert call_args[2]["role"] == "assistant"
            assert "continuity" in call_args[2]["content"]
            assert call_args[3]["role"] == "user"
            assert "Question:" in call_args[3]["content"]

    def test_no_history_two_messages(self):
        """Without history, LLM receives only system + user messages."""
        profile = paragpt_profile()
        gen_fn = make_in_persona_generator(profile)

        state = {
            "query_text": "What is connectivity?",
            "assembled_context": "[1] Connectivity means...",
            "user_memory": "",
            "conversation_history": "",
            "intent_class": "factual",
            "response_tokens": 200,
        }

        with patch("core.langgraph.nodes.generation_nodes.get_llm") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "Connectivity is a framework [1]."
            mock_llm.return_value.invoke.return_value = mock_response

            gen_fn(state)

            call_args = mock_llm.return_value.invoke.call_args[0][0]
            assert len(call_args) == 2  # system + user only
            assert call_args[0]["role"] == "system"
            assert call_args[1]["role"] == "user"


# ===========================================================================
# Mem0 injection — from test_session43
# ===========================================================================

class TestMem0Injection:
    """Mem0 memory injected into system prompt, not user message."""

    def test_memory_in_system_prompt(self):
        profile = paragpt_profile()
        gen_fn = make_in_persona_generator(profile)

        state = {
            "query_text": "What about India?",
            "assembled_context": "",
            "user_memory": "User is from India, interested in infrastructure",
            "conversation_history": "",
            "intent_class": "factual",
            "response_tokens": 200,
        }

        with patch("core.langgraph.nodes.generation_nodes.get_llm") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "India's infrastructure is booming."
            mock_llm.return_value.invoke.return_value = mock_response

            gen_fn(state)

            call_args = mock_llm.return_value.invoke.call_args[0][0]
            system_msg = call_args[0]["content"]
            user_msg = call_args[1]["content"]

            # Memory should be in system prompt
            assert "User is from India" in system_msg
            assert "remember the following" in system_msg
            # Memory should NOT be in user message
            assert "User is from India" not in user_msg

    def test_no_memory_no_injection(self):
        profile = paragpt_profile()
        gen_fn = make_in_persona_generator(profile)

        state = {
            "query_text": "What is ASEAN?",
            "assembled_context": "",
            "user_memory": "",
            "conversation_history": "",
            "intent_class": "factual",
            "response_tokens": 200,
        }

        with patch("core.langgraph.nodes.generation_nodes.get_llm") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "ASEAN is a regional bloc."
            mock_llm.return_value.invoke.return_value = mock_response

            gen_fn(state)

            call_args = mock_llm.return_value.invoke.call_args[0][0]
            system_msg = call_args[0]["content"]
            assert "remember the following" not in system_msg


# ===========================================================================
# Guardrails in generation — from test_session43
# ===========================================================================

class TestGuardrailsInGeneration:
    """Generation node passes guardrails through to LLM system prompt."""

    def test_paragpt_system_prompt_has_guardrails(self):
        profile = paragpt_profile()
        gen_fn = make_in_persona_generator(profile)

        state = {
            "query_text": "What is connectivity?",
            "assembled_context": "",
            "user_memory": "",
            "conversation_history": "",
            "intent_class": "factual",
            "response_tokens": 200,
        }

        with patch("core.langgraph.nodes.generation_nodes.get_llm") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "Connectivity is key."
            mock_llm.return_value.invoke.return_value = mock_response

            gen_fn(state)

            call_args = mock_llm.return_value.invoke.call_args[0][0]
            system_msg = call_args[0]["content"]
            assert "GUARDRAILS" in system_msg
            assert "Persona Integrity" in system_msg

    def test_sacred_archive_system_prompt_has_guardrails(self):
        profile = sacred_archive_profile()
        gen_fn = make_in_persona_generator(profile)

        state = {
            "query_text": "What is compassion?",
            "assembled_context": "[1] Compassion is...",
            "user_memory": "",
            "conversation_history": "",
            "intent_class": "factual",
            "response_tokens": 200,
        }

        with patch("core.langgraph.nodes.generation_nodes.get_llm") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "Compassion is the heart. [1]"
            mock_llm.return_value.invoke.return_value = mock_response

            gen_fn(state)

            call_args = mock_llm.return_value.invoke.call_args[0][0]
            system_msg = call_args[0]["content"]
            assert "GUARDRAILS" in system_msg
            assert "0.95" in system_msg
