"""
LLM Client Factory

Provides a configurable ChatOpenAI instance for any OpenAI-compatible API.
Model, base URL, and API key are all env-var driven for easy experimentation.

Supports OpenRouter (400+ models), Groq, SGLang, vLLM, or any OpenAI-compatible
provider. Defaults to Groq-hosted qwen/qwen3-32b if no LLM_* env vars are set.

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
        max_tokens: Maximum output tokens. None = 2048 (safe default).
                   OpenRouter reserves max_tokens against your credit balance,
                   so leaving it unlimited (model default = 65K+) burns credits.
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

    # Qwen3/3.5 models are "thinking" models — they burn tokens on internal
    # reasoning (<think> tags) unless told not to. Suppression method varies:
    #   - Groq: reasoning_effort="none" as a top-level ChatOpenAI param
    #   - OpenRouter: reasoning={"effort": "none"} via extra_body (NOT model_kwargs,
    #     because LangChain intercepts "reasoning" in model_kwargs and switches to
    #     structured content blocks — breaking pipeline code that expects str content)
    # Without suppression: 1,268 reasoning tokens, 7s for "hello".
    # With suppression: 0 reasoning tokens, 0.9s.
    kwargs: dict = {}
    extra_body: dict = {}
    is_qwen = "qwen" in effective_model.lower()
    if is_qwen:
        if "groq" in LLM_BASE_URL.lower():
            kwargs["reasoning_effort"] = "none"
        else:
            # extra_body sends params directly in HTTP body, bypassing LangChain
            extra_body["reasoning"] = {"effort": "none"}

    # Default to 2048 tokens if not specified. OpenRouter reserves max_tokens
    # against your credit balance — None would request the model's full context
    # (e.g. 65K for Llama 3.3), burning all credits on a single call.
    effective_max_tokens = max_tokens if max_tokens is not None else 2048

    return ChatOpenAI(
        model=effective_model,
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        temperature=temperature,
        max_tokens=effective_max_tokens,
        timeout=30,
        max_retries=2,
        model_kwargs=kwargs,
        extra_body=extra_body or None,
    )
