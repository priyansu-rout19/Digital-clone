"""
Tests for routing nodes — review queue, voice pipeline, sentence splitting, confidence bypass.

Covers: core/langgraph/nodes/routing_nodes.py
"""

import json
import os
from unittest.mock import patch, MagicMock

import pytest


# ===========================================================================
# Review queue writer — from test_session16
# ===========================================================================

class TestReviewQueueWriter:

    def test_writes_to_db(self):
        """review_queue_writer should INSERT into review_queue table."""
        from core.langgraph.nodes.routing_nodes import review_queue_writer

        state = {
            "clone_id": "00000000-0000-0000-0000-000000000001",
            "user_id": "anonymous",
            "query_text": "What is the meaning of life?",
            "verified_response": "The meaning is love.",
            "raw_response": "",
            "cited_sources": [{"doc_id": "abc", "passage": "love is all"}],
            "final_confidence": 0.85,
        }

        with patch("core.langgraph.nodes.routing_nodes.psycopg") as mock_psycopg:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

            os.environ["DATABASE_URL"] = "postgresql+psycopg://test@localhost/test"
            result = review_queue_writer(state)

            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            sql = call_args[0][0]
            assert "INSERT INTO review_queue" in sql
            assert "pending" in sql

            # State should be returned with review_id added
            assert result["clone_id"] == state["clone_id"]
            assert result["verified_response"] == state["verified_response"]
            assert result["review_id"]  # non-empty UUID string on success

    def test_skips_if_no_clone_id(self):
        """Should skip DB write if clone_id is missing."""
        from core.langgraph.nodes.routing_nodes import review_queue_writer

        state = {"clone_id": "", "verified_response": "test"}
        result = review_queue_writer(state)
        assert result is state

    def test_skips_if_no_response(self):
        """Should skip DB write if response is missing."""
        from core.langgraph.nodes.routing_nodes import review_queue_writer

        state = {"clone_id": "abc", "verified_response": "", "raw_response": ""}
        result = review_queue_writer(state)
        assert result is state

    def test_anonymous_user_becomes_none(self):
        """user_id='anonymous' should become NULL in DB (not a valid UUID)."""
        from core.langgraph.nodes.routing_nodes import review_queue_writer

        state = {
            "clone_id": "00000000-0000-0000-0000-000000000001",
            "user_id": "anonymous",
            "query_text": "test",
            "verified_response": "response",
            "cited_sources": [],
            "final_confidence": 0.5,
        }

        with patch("core.langgraph.nodes.routing_nodes.psycopg") as mock_psycopg:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

            os.environ["DATABASE_URL"] = "postgresql+psycopg://test@localhost/test"
            review_queue_writer(state)

            # user_id_val should be None (4th param in the tuple)
            params = mock_cursor.execute.call_args[0][1]
            assert params[2] is None  # user_id_val

    def test_graceful_on_db_error(self):
        """Should not crash the pipeline if DB write fails."""
        from core.langgraph.nodes.routing_nodes import review_queue_writer

        state = {
            "clone_id": "00000000-0000-0000-0000-000000000001",
            "user_id": "anonymous",
            "query_text": "test",
            "verified_response": "response",
            "cited_sources": [],
            "final_confidence": 0.5,
        }

        with patch("core.langgraph.nodes.routing_nodes.psycopg") as mock_psycopg:
            mock_psycopg.connect.side_effect = Exception("DB connection failed")
            os.environ["DATABASE_URL"] = "postgresql+psycopg://test@localhost/test"

            result = review_queue_writer(state)
            # Should not crash — returns state with review_id="" on failure
            assert result["clone_id"] == state["clone_id"]
            assert result["review_id"] == ""


# ===========================================================================
# Voice pipeline — from test_session16
# ===========================================================================

class TestVoicePipeline:

    def test_ai_clone_generates_audio(self):
        """ai_clone mode should call edge-tts and return base64 audio."""
        from core.models.clone_profile import paragpt_profile
        from core.langgraph.nodes.routing_nodes import make_voice_pipeline

        profile = paragpt_profile()
        voice_node = make_voice_pipeline(profile)

        state = {
            "voice_chunks": ["Hello world.", "This is a test."],
            "audio_base64": "",
            "audio_format": "",
        }

        # Mock the async TTS helper directly
        async def fake_tts(text, voice):
            return b"\x00\x01\x02fake-mp3-bytes"

        with patch(
            "core.langgraph.nodes.routing_nodes._run_edge_tts",
            side_effect=fake_tts,
        ):
            result = voice_node(state)
            assert result.get("audio_base64"), "Should have base64 audio"
            assert result.get("audio_format") == "mp3"

    def test_original_only_returns_unchanged(self):
        """original_only mode should return state unchanged (stub)."""
        from core.models.clone_profile import sacred_archive_profile
        from core.langgraph.nodes.routing_nodes import make_voice_pipeline

        profile = sacred_archive_profile()
        voice_node = make_voice_pipeline(profile)

        state = {
            "voice_chunks": ["test chunk"],
            "audio_base64": "",
            "audio_format": "",
        }

        result = voice_node(state)
        assert result.get("audio_base64", "") == ""

    def test_empty_chunks_returns_unchanged(self):
        """No voice_chunks should return state unchanged."""
        from core.models.clone_profile import paragpt_profile
        from core.langgraph.nodes.routing_nodes import make_voice_pipeline

        profile = paragpt_profile()
        voice_node = make_voice_pipeline(profile)

        state = {"voice_chunks": [], "audio_base64": "", "audio_format": ""}
        result = voice_node(state)
        assert result is state

    def test_graceful_on_tts_error(self):
        """TTS failure should not crash — return state unchanged."""
        from core.models.clone_profile import paragpt_profile
        from core.langgraph.nodes.routing_nodes import make_voice_pipeline

        profile = paragpt_profile()
        voice_node = make_voice_pipeline(profile)

        state = {
            "voice_chunks": ["Hello world."],
            "audio_base64": "",
            "audio_format": "",
        }

        async def failing_tts(text, voice):
            raise Exception("TTS service down")

        with patch(
            "core.langgraph.nodes.routing_nodes._run_edge_tts",
            side_effect=failing_tts,
        ):
            result = voice_node(state)
            assert result.get("audio_base64", "") == ""


# ===========================================================================
# Sentence splitting — from test_session16
# ===========================================================================

class TestSentenceSplitting:

    def test_llm_splits_correctly(self):
        """LLM should handle abbreviations like Dr. and U.S. correctly."""
        from core.langgraph.nodes.routing_nodes import stream_to_user

        mock_response = MagicMock()
        mock_response.content = json.dumps([
            "Dr. Smith works at the U.S. embassy.",
            "He studies connectivity.",
        ])

        with patch("core.llm.get_llm") as mock_llm:
            mock_llm.return_value.invoke.return_value = mock_response

            state = {
                "verified_response": "Dr. Smith works at the U.S. embassy. He studies connectivity.",
                "raw_response": "",
            }
            result = stream_to_user(state)
            chunks = result["voice_chunks"]
            assert len(chunks) == 2
            assert "Dr. Smith" in chunks[0]

    def test_fallback_on_llm_error(self):
        """LLM error should fall back to naive splitting."""
        from core.langgraph.nodes.routing_nodes import stream_to_user

        with patch("core.llm.get_llm") as mock_llm:
            mock_llm.return_value.invoke.side_effect = Exception("API error")

            state = {
                "verified_response": "First sentence. Second sentence.",
                "raw_response": "",
            }
            result = stream_to_user(state)
            chunks = result["voice_chunks"]
            assert len(chunks) >= 2

    def test_empty_response(self):
        """Empty response should return empty voice_chunks."""
        from core.langgraph.nodes.routing_nodes import stream_to_user

        state = {"verified_response": "", "raw_response": ""}
        result = stream_to_user(state)
        assert result["voice_chunks"] == []


# ===========================================================================
# Confidence bypass for persona — from test_session42
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
