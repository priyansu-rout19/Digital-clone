import os
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings


load_dotenv()


class EmbeddingClient:

    def __init__(self, base_url: str, model: str, api_key: str):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self._client: Optional[OpenAIEmbeddings] = None

    def _init_client(self) -> None:
        self._client = OpenAIEmbeddings(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _is_openai_model(self) -> bool:
        return self.model.startswith("text-embedding-3-")

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        if not self._client:
            self._init_client()

        try:
            if self._is_openai_model():
                embeddings = self._client.embed_documents(
                    batch,
                    dimensions=1024,
                )
            else:
                embeddings = self._client.embed_documents(batch)

            return embeddings

        except Exception as e:
            raise ValueError(f"Embedding API failed: {str(e)}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        batch_size = 32
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


def get_embedder() -> EmbeddingClient:
    base_url = os.environ.get("EMBEDDING_API_BASE_URL")
    if not base_url:
        raise KeyError(
            "EMBEDDING_API_BASE_URL environment variable not set. "
            "Please set it to https://api.openai.com/v1 (dev) or http://localhost:8001/v1 (prod)"
        )

    model = os.environ.get("EMBEDDING_MODEL")
    if not model:
        raise KeyError(
            "EMBEDDING_MODEL environment variable not set. "
            "Please set it to text-embedding-3-small (dev) or Qwen3-Embedding-0.6B (prod)"
        )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise KeyError(
            "OPENAI_API_KEY environment variable not set. "
            "Please create a .env file with OPENAI_API_KEY=<your_key> (required for dev mode)"
        )

    return EmbeddingClient(
        base_url=base_url,
        model=model,
        api_key=api_key,
    )
