"""
Mem0 Client Factory

Provides a configured Mem0 instance for cross-session user memory with pgvector backend.
Reads configuration from environment variables.

Uses:
- LLM: Groq API + qwen/qwen3-32b (same as core/llm.py)
- Embedder: Voyage AI voyage-3 with 1024 dimensions
- Vector Store: PostgreSQL pgvector (same DB as documents)
"""

import os
from urllib.parse import urlparse
from dotenv import load_dotenv
from mem0 import Memory
from langchain_voyageai import VoyageAIEmbeddings


load_dotenv()


def _parse_database_url(db_url: str) -> dict:
    """
    Parse PostgreSQL DATABASE_URL into pgvector config fields.

    Example input: postgresql://user:pass@localhost:5432/mydb
    Returns: {host, port, dbname, user, password}
    """
    parsed = urlparse(db_url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "dbname": parsed.path.lstrip("/"),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
    }


def get_mem0_client() -> Memory:
    """
    Get a configured Mem0 instance for cross-session user memory.

    Uses pgvector backend in the same PostgreSQL database as the application.
    LLM uses Groq API, embedder uses Voyage AI (same as core/rag/ingestion/embedder.py).

    Returns:
        Memory instance ready to search() and add() memories

    Raises:
        KeyError: If required environment variables are not set
    """

    # Check required env vars
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise KeyError(
            "DATABASE_URL environment variable not set. "
            "Please set it to your PostgreSQL connection string (e.g., "
            "postgresql://postgres:password@localhost:5432/digital_clone)"
        )

    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        raise KeyError(
            "GROQ_API_KEY environment variable not set. "
            "Please create a .env file with GROQ_API_KEY=<your_key>"
        )

    voyage_key = os.environ.get("VOYAGE_API_KEY")
    if not voyage_key:
        raise KeyError(
            "VOYAGE_API_KEY environment variable not set. "
            "Please create a .env file with VOYAGE_API_KEY=<your_key>"
        )

    # Parse DB URL for pgvector config
    db_config = _parse_database_url(db_url)

    # Build Mem0 config
    config = {
        "llm": {
            "provider": "groq",
            "config": {
                "model": "qwen/qwen3-32b",
                "api_key": groq_key,
            },
        },
        "embedder": {
            "provider": "langchain",
            "config": {
                "langchain_embeddings": VoyageAIEmbeddings(model="voyage-3"),
                "embedding_dims": 1024,
            },
        },
        "vector_store": {
            "provider": "pgvector",
            "config": {
                "host": db_config["host"],
                "port": db_config["port"],
                "dbname": db_config["dbname"],
                "user": db_config["user"],
                "password": db_config["password"],
                "embedding_model_dims": 1024,
            },
        },
    }

    return Memory.from_config(config)
