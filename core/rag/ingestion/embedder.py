import os
import time
import logging
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings


load_dotenv()

logger = logging.getLogger(__name__)

# Truncation target — Gemini outputs 3072 dims, we truncate to 1024
# for pgvector compatibility (Matryoshka property preserves quality)
TARGET_DIMS = 1024

# Retry settings for transient API errors (429, 5xx)
MAX_RETRIES = 3
BACKOFF_BASE_S = 1.0  # 1s, 2s, 4s


class EmbeddingClient:

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key
        self._client: GoogleGenerativeAIEmbeddings | None = None

    def _init_client(self) -> None:
        self._client = GoogleGenerativeAIEmbeddings(
            model=self.model,
            google_api_key=self.api_key,
        )

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        if not self._client:
            self._init_client()

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                embeddings = self._client.embed_documents(batch)
                return [v[:TARGET_DIMS] for v in embeddings]
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                is_retryable = "429" in err_str or "rate" in err_str or "500" in err_str or "503" in err_str
                if is_retryable and attempt < MAX_RETRIES:
                    delay = BACKOFF_BASE_S * (2 ** attempt)
                    logger.warning(f"Embedding API error (attempt {attempt + 1}/{MAX_RETRIES + 1}), retrying in {delay}s: {e}")
                    time.sleep(delay)
                    continue
                break

        raise ValueError(f"Embedding API failed after {MAX_RETRIES + 1} attempts: {last_error}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                batch_embeddings = self._embed_batch(batch)
                all_embeddings.extend(batch_embeddings)
            except ValueError as e:
                raise ValueError(
                    f"Embedding failed for batch {i // batch_size} (texts {i}-{min(i + batch_size, len(texts))}): {str(e)}"
                )

        return all_embeddings


# Module-level singleton — avoids creating a new client per request
_cached_embedder: EmbeddingClient | None = None
_cached_key: str | None = None


def get_embedder() -> EmbeddingClient:
    global _cached_embedder, _cached_key

    model = os.environ.get("EMBEDDING_MODEL")
    if not model:
        raise KeyError(
            "EMBEDDING_MODEL environment variable not set. "
            "Please set it to models/gemini-embedding-001"
        )

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise KeyError(
            "GOOGLE_API_KEY environment variable not set. "
            "Please create a .env file with GOOGLE_API_KEY=<your_key>"
        )

    # Return cached instance if key hasn't changed
    if _cached_embedder is not None and api_key == _cached_key:
        return _cached_embedder

    _cached_embedder = EmbeddingClient(model=model, api_key=api_key)
    _cached_key = api_key
    return _cached_embedder
