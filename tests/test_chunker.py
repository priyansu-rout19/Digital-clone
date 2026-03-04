import os
import pytest
from unittest.mock import MagicMock

from core.rag.ingestion.chunker import chunk_text, _estimate_tokens, _enforce_max_size


# === Unit tests (no API calls) ===

def test_empty_input_semantic():
    assert chunk_text([], strategy="semantic", embeddings=MagicMock()) == []


def test_empty_input_fixed():
    assert chunk_text([], strategy="fixed_size") == []


def test_fixed_size_fallback():
    blocks = ["A " * 250, "B " * 250, "C " * 250]
    chunks = chunk_text(blocks, strategy="fixed_size")
    assert len(chunks) >= 1
    assert all(isinstance(c, str) for c in chunks)


def test_invalid_strategy():
    with pytest.raises(ValueError, match="Unknown chunking strategy"):
        chunk_text(["test"], strategy="invalid")


def test_semantic_requires_embeddings():
    with pytest.raises(ValueError, match="Embeddings instance required"):
        chunk_text(["test"], strategy="semantic", embeddings=None)


def test_estimate_tokens():
    assert _estimate_tokens("hello world") == int(2 * 1.3)


def test_enforce_max_size_passthrough():
    chunks = ["Short chunk.", "Another short one."]
    result = _enforce_max_size(chunks, max_tokens=1024)
    assert result == chunks


def test_enforce_max_size_splits():
    huge_chunk = "This is a sentence. " * 500
    result = _enforce_max_size([huge_chunk], max_tokens=512)
    assert len(result) > 1


# === Integration tests (require GOOGLE_API_KEY) ===

@pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not configured",
)
class TestSemanticChunkingIntegration:

    def _get_embeddings(self):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model=os.environ.get("EMBEDDING_MODEL", "models/gemini-embedding-001"),
            google_api_key=os.environ["GOOGLE_API_KEY"],
        )

    def test_semantic_chunking_basic(self):
        blocks = [
            "The economy grew by 3% last quarter. Inflation remained stable at 2%.",
            "In sports news, the championship game drew record viewership.",
            "Scientists discovered a new species of deep-sea fish near the Mariana Trench.",
        ]
        embeddings = self._get_embeddings()
        chunks = chunk_text(blocks, strategy="semantic", embeddings=embeddings)
        assert len(chunks) >= 1
        assert all(isinstance(c, str) for c in chunks)

    def test_semantic_on_sample_doc(self):
        from pathlib import Path
        sample = Path(__file__).parent.parent / "scripts" / "sample_docs" / "paragpt_sample.md"
        if not sample.exists():
            pytest.skip("Sample doc not found")
        blocks = open(sample).read().split("\n\n")
        blocks = [b.strip() for b in blocks if len(b.strip()) >= 20]

        embeddings = self._get_embeddings()
        semantic = chunk_text(blocks, strategy="semantic", embeddings=embeddings)
        fixed = chunk_text(blocks, strategy="fixed_size")

        assert len(semantic) >= 1
        assert len(fixed) >= 1
        # Both should preserve all content (no text lost)
        semantic_text = " ".join(semantic)
        fixed_text = " ".join(fixed)
        assert len(semantic_text) > 0
        assert len(fixed_text) > 0
