"""
Session 43 Verification Tests — Fix 5 Fundamental Failures + Externalized Profiles

Tests cover:
  Fix 1: Pre-filter (single-word greetings only)
  Fix 2: Rich persona document on ParaGPT profile
  Fix 3: Adaptive generation prompts by binary intent (persona | retrieval)
  Fix 4: Confidence scoring — no history inflation
  Fix 5: Context bleed fix — history/context separation in messages
  Fix 6: Mem0 injection moved from user message to system prompt
  Externalized Profiles: soul.md + guardrails.md loaded into CloneProfile
"""

import pytest
from unittest.mock import patch, MagicMock

from core.langgraph.nodes.query_analysis_node import (
    _prefilter,
    _persona_result,
    query_analysis,
)
from core.langgraph.nodes.generation_nodes import (
    make_in_persona_generator,
    confidence_scorer,
)
from core.models.clone_profile import (
    paragpt_profile, sacred_archive_profile,
    load_profile_markdown, CloneProfile,
)
from core.prompts import interpretive_generator_prompt, mirror_only_generator_prompt


# ── Fix 1: Pre-filter (Single-Word Greetings) ──────────────────


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


# ── Fix 2: Rich Persona Document ────────────────────────────────


class TestPersonaDocument:
    """ParaGPT has a rich persona, Sacred Archive has none."""

    def test_paragpt_persona_nonempty(self):
        profile = paragpt_profile()
        assert profile.persona_document != ""
        assert len(profile.persona_document) > 200

    def test_paragpt_persona_has_layers(self):
        doc = paragpt_profile().persona_document
        assert "Who I Am" in doc
        assert "How I Talk" in doc
        assert "How I Interact" in doc
        assert "What I Won't Do" in doc

    def test_paragpt_persona_has_key_facts(self):
        doc = paragpt_profile().persona_document
        assert "Singapore" in doc
        assert "Connectography" in doc
        assert "FutureMap" in doc

    def test_sacred_archive_persona_from_file(self):
        """Sacred Archive now has a persona loaded from soul.md."""
        profile = sacred_archive_profile()
        assert profile.persona_document != ""
        assert "sacred mirror" in profile.persona_document

    def test_persona_document_hydrated_from_disk(self):
        """Known slugs get persona_document hydrated from soul.md even if missing from input."""
        profile = paragpt_profile()
        data = profile.model_dump()
        del data["persona_document"]
        from core.models.clone_profile import CloneProfile
        restored = CloneProfile(**data)
        # Validator hydrates from profiles/paragpt-client/soul.md
        assert restored.persona_document != ""
        assert "Parag Khanna" in restored.persona_document


# ── Fix 3: Adaptive Generation Prompts (Binary Intent) ──────────


class TestAdaptivePrompts:
    """Citation/tone instructions change based on binary intent."""

    def test_persona_no_cite(self):
        prompt = interpretive_generator_prompt("Test", "Bio", intent_class="persona")
        assert "No citations needed" in prompt
        assert "Never fabricate biographical facts" in prompt

    def test_retrieval_cite(self):
        prompt = interpretive_generator_prompt("Test", "Bio", intent_class="retrieval")
        assert "Cite sources" in prompt
        assert "cite densely" in prompt

    def test_default_is_retrieval(self):
        """Default intent_class='retrieval'; unknown values also fall into else branch."""
        prompt = interpretive_generator_prompt("Test", "Bio", intent_class="factual")
        assert "Cite sources" in prompt

    def test_persona_injected_into_prompt(self):
        prompt = interpretive_generator_prompt("PK", "Bio text", persona_document="I grew up globally")
        assert "I grew up globally" in prompt
        assert "You are PK" in prompt


# ── Fix 4: Confidence Scoring ────────────────────────────────────


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


# ── Fix 5: Context Bleed Fix ────────────────────────────────────


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


# ── Fix 6: Mem0 in System Prompt ────────────────────────────────


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


# ── Externalized Profiles: soul.md + guardrails.md ────────────


class TestLoadProfileMarkdown:
    """load_profile_markdown() reads files from profiles/ directory."""

    def test_paragpt_soul_loads(self):
        content = load_profile_markdown("paragpt-client", "soul.md")
        assert len(content) > 100
        assert "Who I Am" in content

    def test_paragpt_guardrails_loads(self):
        content = load_profile_markdown("paragpt-client", "guardrails.md")
        assert len(content) > 100
        assert "Citation Behavior" in content

    def test_sacred_archive_soul_loads(self):
        content = load_profile_markdown("sacred-archive", "soul.md")
        assert len(content) > 100
        assert "sacred mirror" in content

    def test_sacred_archive_guardrails_loads(self):
        content = load_profile_markdown("sacred-archive", "guardrails.md")
        assert len(content) > 100
        assert "Confidence & Silence" in content

    def test_missing_file_returns_empty(self):
        """Graceful degradation: missing file returns empty string."""
        content = load_profile_markdown("nonexistent-slug", "soul.md")
        assert content == ""

    def test_missing_filename_returns_empty(self):
        content = load_profile_markdown("paragpt-client", "nonexistent.md")
        assert content == ""


class TestExternalizedProfiles:
    """Factory functions load persona + guardrails from markdown files."""

    def test_paragpt_persona_from_markdown(self):
        profile = paragpt_profile()
        assert profile.persona_document != ""
        assert "Who I Am" in profile.persona_document
        assert "Singapore" in profile.persona_document
        assert "Connectography" in profile.persona_document

    def test_paragpt_guardrails_from_markdown(self):
        profile = paragpt_profile()
        assert profile.guardrails_document != ""
        assert "Citation Behavior" in profile.guardrails_document
        assert "Persona Integrity" in profile.guardrails_document

    def test_sacred_archive_persona_from_markdown(self):
        profile = sacred_archive_profile()
        assert profile.persona_document != ""
        assert "sacred mirror" in profile.persona_document

    def test_sacred_archive_guardrails_from_markdown(self):
        profile = sacred_archive_profile()
        assert profile.guardrails_document != ""
        assert "0.95" in profile.guardrails_document

    def test_guardrails_document_hydrated_from_disk(self):
        """Known slugs get guardrails_document hydrated from guardrails.md even if missing from input."""
        profile = paragpt_profile()
        data = profile.model_dump()
        del data["guardrails_document"]
        restored = CloneProfile(**data)
        # Validator hydrates from profiles/paragpt-client/guardrails.md
        assert restored.guardrails_document != ""
        assert "Persona Integrity" in restored.guardrails_document


class TestGuardrailsInPrompts:
    """Guardrails injected into system prompts when provided."""

    def test_interpretive_prompt_includes_guardrails(self):
        prompt = interpretive_generator_prompt(
            "Test", "Bio",
            guardrails_document="No speculation allowed.",
            intent_class="factual",
        )
        assert "GUARDRAILS" in prompt
        assert "No speculation allowed." in prompt

    def test_interpretive_prompt_no_guardrails_when_empty(self):
        prompt = interpretive_generator_prompt("Test", "Bio", guardrails_document="")
        assert "GUARDRAILS" not in prompt

    def test_mirror_only_prompt_includes_guardrails(self):
        prompt = mirror_only_generator_prompt(guardrails_document="Quote-only mode.")
        assert "GUARDRAILS" in prompt
        assert "Quote-only mode." in prompt

    def test_mirror_only_prompt_no_guardrails_when_empty(self):
        prompt = mirror_only_generator_prompt(guardrails_document="")
        assert "GUARDRAILS" not in prompt

    def test_mirror_only_prompt_still_has_base_rules(self):
        prompt = mirror_only_generator_prompt()
        assert "direct quotes" in prompt
        assert "source number [1]" in prompt


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


# ── Fix: Hydrate Markdown Documents Validator ────────────────────


class TestHydrateMarkdownDocuments:
    """model_validator always loads persona/guardrails from disk (source of truth)."""

    def test_db_loaded_profile_gets_hydrated(self):
        """Simulates the exact bug: construct with persona_document='', verify hydration."""
        profile = paragpt_profile()
        data = profile.model_dump()
        # Simulate stale DB row: persona and guardrails empty (pre-S43 seed)
        data["persona_document"] = ""
        data["guardrails_document"] = ""
        restored = CloneProfile(**data)
        # Validator must hydrate from disk
        assert restored.persona_document != ""
        assert "Parag Khanna" in restored.persona_document
        assert restored.guardrails_document != ""
        assert "Persona Integrity" in restored.guardrails_document

    def test_unknown_slug_keeps_defaults(self):
        """Slug with no profile directory → stays empty (graceful degradation)."""
        profile = paragpt_profile()
        data = profile.model_dump()
        data["slug"] = "nonexistent-clone"
        data["persona_document"] = ""
        data["guardrails_document"] = ""
        restored = CloneProfile(**data)
        # No files on disk for this slug, should stay empty
        assert restored.persona_document == ""
        assert restored.guardrails_document == ""

    def test_factory_and_validator_produce_same_result(self):
        """DB round-trip produces identical persona content as factory."""
        factory_profile = paragpt_profile()
        # Simulate DB round-trip: dump to dict (JSONB), reconstruct
        data = factory_profile.model_dump()
        db_profile = CloneProfile(**data)
        assert db_profile.persona_document == factory_profile.persona_document
        assert db_profile.guardrails_document == factory_profile.guardrails_document
