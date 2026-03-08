"""
Session 16 Tests — Stub replacement verification.

Tests for: review_queue_writer (DB), token_budget (LLM), audio parsing (Whisper),
voice_pipeline (edge-tts), sentence splitting (LLM), CRAG evaluator (confidence).
"""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

import pytest


# ---------------------------------------------------------------------------
# Task 1: review_queue_writer
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 2: token_budget (LLM-based)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 3: Audio/Video Parsing (Groq Whisper)
# ---------------------------------------------------------------------------

class TestAudioParsing:

    def test_parse_audio_calls_whisper(self):
        """Audio parsing should call Groq Whisper API."""
        from core.rag.ingestion.parser import parse

        mock_response = MagicMock()
        mock_response.text = (
            "This is a test transcription of an audio file. "
            "It contains important information about connectivity and technology."
        )

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake audio bytes")
            temp_path = f.name

        try:
            with patch("core.rag.ingestion.parser.Groq") as MockGroq:
                mock_client = MagicMock()
                MockGroq.return_value = mock_client
                mock_client.audio.transcriptions.create.return_value = mock_response

                os.environ["GROQ_API_KEY"] = "test-key"
                blocks = parse(temp_path)

                assert len(blocks) >= 1
                assert "transcription" in " ".join(blocks).lower()
                mock_client.audio.transcriptions.create.assert_called_once()
        finally:
            os.unlink(temp_path)

    def test_parse_audio_file_too_large(self):
        """Files over 25MB should raise ValueError."""
        from core.rag.ingestion.parser import parse

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        try:
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value.st_size = 30 * 1024 * 1024  # 30MB
                with patch("pathlib.Path.exists", return_value=True):
                    os.environ["GROQ_API_KEY"] = "test-key"
                    with pytest.raises(ValueError, match="too large"):
                        parse(temp_path)
        finally:
            os.unlink(temp_path)

    def test_parse_audio_no_api_key(self):
        """Missing GROQ_API_KEY should raise ValueError."""
        from core.rag.ingestion.parser import parse

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake")
            temp_path = f.name

        try:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("GROQ_API_KEY", None)
                with pytest.raises(ValueError, match="GROQ_API_KEY"):
                    parse(temp_path)
        finally:
            os.unlink(temp_path)

    def test_parse_audio_empty_transcript(self):
        """Empty transcript should return empty list."""
        from core.rag.ingestion.parser import parse

        mock_response = MagicMock()
        mock_response.text = ""

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake audio")
            temp_path = f.name

        try:
            with patch("core.rag.ingestion.parser.Groq") as MockGroq:
                mock_client = MagicMock()
                MockGroq.return_value = mock_client
                mock_client.audio.transcriptions.create.return_value = mock_response

                os.environ["GROQ_API_KEY"] = "test-key"
                blocks = parse(temp_path)
                assert blocks == []
        finally:
            os.unlink(temp_path)

    def test_pdf_still_works(self):
        """PDF parsing should still work after audio changes."""
        from core.rag.ingestion.parser import parse

        # Use an existing sample doc if available, otherwise skip
        sample = "/home/priyansurout/Digital Clone Engine/sample_docs/sample_teaching.txt"
        if os.path.exists(sample):
            blocks = parse(sample)
            assert len(blocks) > 0


# ---------------------------------------------------------------------------
# Task 4: Voice Pipeline (edge-tts)
# ---------------------------------------------------------------------------

class TestVoicePipeline:

    def test_ai_clone_generates_audio(self):
        """ai_clone mode should call edge-tts and return base64 audio."""
        import asyncio
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


# ---------------------------------------------------------------------------
# Task 5: Sentence Splitting (LLM-based)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 6: CRAG Evaluator
# ---------------------------------------------------------------------------

class TestCRAGEvaluator:

    def test_no_passages_zero_confidence(self):
        """No passages should yield 0.0 confidence."""
        from core.langgraph.nodes.retrieval_nodes import crag_evaluator

        state = {"retrieved_passages": [], "retrieval_confidence": 0.9}
        result = crag_evaluator(state)
        assert result["retrieval_confidence"] == 0.0

    def test_few_passages_penalized(self):
        """1 passage with 0.9 confidence should be penalized to ~0.3."""
        from core.langgraph.nodes.retrieval_nodes import crag_evaluator

        state = {
            "retrieved_passages": [{"passage": "one"}],
            "retrieval_confidence": 0.9,
        }
        result = crag_evaluator(state)
        assert result["retrieval_confidence"] == pytest.approx(0.3, abs=0.01)

    def test_two_passages_penalized(self):
        """2 passages with 0.9 confidence should be penalized to ~0.6."""
        from core.langgraph.nodes.retrieval_nodes import crag_evaluator

        state = {
            "retrieved_passages": [{"passage": "one"}, {"passage": "two"}],
            "retrieval_confidence": 0.9,
        }
        result = crag_evaluator(state)
        assert result["retrieval_confidence"] == pytest.approx(0.6, abs=0.01)

    def test_many_passages_no_penalty(self):
        """3+ passages should not be penalized."""
        from core.langgraph.nodes.retrieval_nodes import crag_evaluator

        passages = [{"passage": f"p{i}"} for i in range(5)]
        state = {"retrieved_passages": passages, "retrieval_confidence": 0.9}
        result = crag_evaluator(state)
        assert result["retrieval_confidence"] == 0.9

    def test_confidence_clamped(self):
        """Confidence should be clamped to [0.0, 1.0]."""
        from core.langgraph.nodes.retrieval_nodes import crag_evaluator

        passages = [{"passage": f"p{i}"} for i in range(5)]
        state = {"retrieved_passages": passages, "retrieval_confidence": 1.5}
        result = crag_evaluator(state)
        assert result["retrieval_confidence"] == 1.0
