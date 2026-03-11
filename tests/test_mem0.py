"""
Tests for Mem0 client — provider selection logic.

Covers: core/mem0_client.py
"""

import os
from unittest.mock import patch, MagicMock

import pytest


# ===========================================================================
# Mem0 config — from test_session42
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
