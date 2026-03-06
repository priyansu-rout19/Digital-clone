"""
LLM Client Factory

Provides a configurable ChatOpenAI instance for any OpenAI-compatible API.
Model, base URL, and API key are all env-var driven for easy experimentation.

Defaults to Groq-hosted qwen/qwen3-32b if no LLM_* env vars are set.

Environment variables:
    LLM_MODEL    — Model identifier (default: qwen/qwen3-32b)
    LLM_BASE_URL — OpenAI-compatible API endpoint (default: Groq)
    LLM_API_KEY  — API key (falls back to GROQ_API_KEY)
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


# Load .env file once at module import time
load_dotenv()

# Resolve config once at import — avoids repeated os.environ lookups
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen/qwen3-32b")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("GROQ_API_KEY")


def get_llm(temperature: float = 0.7, max_tokens: int | None = None,
            model: str | None = None) -> ChatOpenAI:
    """
    Get a configured ChatOpenAI client.

    Args:
        temperature: Controls randomness (0.0 = deterministic, 1.0 = random)
                   Use 0.0 for classification, 0.7 for generation
        max_tokens: Maximum output tokens. None = model default.
        model: Override model ID for this request. None = use LLM_MODEL env var.

    Returns:
        ChatOpenAI instance ready to invoke

    Raises:
        KeyError: If no API key is available
    """
    if not LLM_API_KEY:
        raise KeyError(
            "No LLM API key found. Set LLM_API_KEY or GROQ_API_KEY in .env"
        )

    # Use per-request override if provided, otherwise fall back to env var
    effective_model = model or LLM_MODEL

    # Qwen models on Groq need reasoning_effort=none to suppress <think> tags
    kwargs: dict = {}
    if "qwen" in effective_model.lower():
        kwargs["reasoning_effort"] = "none"

    return ChatOpenAI(
        model=effective_model,
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=30,
        max_retries=2,
        model_kwargs=kwargs,
    )
