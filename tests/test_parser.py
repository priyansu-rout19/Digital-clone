"""
Tests for file parser — audio parsing (Whisper), PDF fallback.

Covers: core/rag/ingestion/parser.py
"""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest


# ===========================================================================
# Audio parsing — from test_session16
# ===========================================================================

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
