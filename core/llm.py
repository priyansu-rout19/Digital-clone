"""
LLM Client Factory

Provides a singleton-like interface to get a configured ChatOpenAI instance
pointing at Groq's OpenAI-compatible API with qwen-qwq-32b model.

API key loaded from environment variable GROQ_API_KEY (via .env file).
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


# Load .env file once at module import time
load_dotenv()


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """
    Get a configured ChatOpenAI client for Groq's qwen-qwq-32b model.

    Args:
        temperature: Controls randomness (0.0 = deterministic, 1.0 = random)
                   Use 0.0 for classification, 0.7 for generation

    Returns:
        ChatOpenAI instance ready to invoke

    Raises:
        KeyError: If GROQ_API_KEY environment variable is not set
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise KeyError(
            "GROQ_API_KEY environment variable not set. "
            "Please create a .env file with GROQ_API_KEY=<your_key>"
        )

    return ChatOpenAI(
        model="qwen/qwen3-32b",  # Groq's Qwen model (aligns with production Qwen3.5-35B)
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        temperature=temperature,
        timeout=30,
        max_retries=2,
        model_kwargs={"reasoning_effort": "none"},  # Disable <think> tags at API level
    )
