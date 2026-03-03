import os
from typing import Optional
from dotenv import load_dotenv
from langchain_voyageai import VoyageAIEmbeddings


load_dotenv()


class EmbeddingClient:

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key
        self._client: Optional[VoyageAIEmbeddings] = None

    def _init_client(self) -> None:
        self._client = VoyageAIEmbeddings(
            model=self.model,
            voyage_api_key=self.api_key,
        )

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        if not self._client:
            self._init_client()

        try:
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
    model = os.environ.get("EMBEDDING_MODEL")
    if not model:
        raise KeyError(
            "EMBEDDING_MODEL environment variable not set. "
            "Please set it to voyage-3 (or other Voyage models)"
        )

    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        raise KeyError(
            "VOYAGE_API_KEY environment variable not set. "
            "Please create a .env file with VOYAGE_API_KEY=<your_key>"
        )

    return EmbeddingClient(
        model=model,
        api_key=api_key,
    )
