"""
Tests for prompt registry — adaptive prompts, guardrails injection.

Covers: core/prompts/registry.py
"""

from core.prompts import interpretive_generator_prompt, mirror_only_generator_prompt


# ===========================================================================
# Adaptive prompts (binary intent) — from test_session43
# ===========================================================================

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


# ===========================================================================
# Guardrails in prompts — from test_session43
# ===========================================================================

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
