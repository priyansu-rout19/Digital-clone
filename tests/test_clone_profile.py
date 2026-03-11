"""
Tests for clone profile — persona documents, markdown loading, hydration.

Covers: core/models/clone_profile.py + profiles/
"""

import pytest

from core.models.clone_profile import (
    paragpt_profile,
    sacred_archive_profile,
    load_profile_markdown,
    CloneProfile,
)


# ===========================================================================
# Persona document — from test_session43
# ===========================================================================

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
        restored = CloneProfile(**data)
        # Validator hydrates from profiles/paragpt-client/soul.md
        assert restored.persona_document != ""
        assert "Parag Khanna" in restored.persona_document


# ===========================================================================
# Load profile markdown — from test_session43
# ===========================================================================

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


# ===========================================================================
# Externalized profiles — from test_session43
# ===========================================================================

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


# ===========================================================================
# Hydrate markdown documents validator — from test_session43
# ===========================================================================

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
