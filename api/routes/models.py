"""
Models Endpoint

Lists available LLM models from the configured provider.
Caches the result for 5 minutes to avoid hammering the provider API.
All OpenAI-compatible APIs (OpenRouter, Groq, SGLang, vLLM) support GET /models.
"""

import time
import logging

import httpx
from fastapi import APIRouter

from core.llm import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory cache: [timestamp, models_list]
_cache: list = [0.0, []]
CACHE_TTL_SECONDS = 300  # 5 minutes

# Model ID substrings to filter out (non-text, niche, or low-quality models).
# OpenRouter returns 400+ models — this keeps the dropdown manageable.
_EXCLUDE_PATTERNS = (
    "whisper", "embed", "guard", "tts", "moderation", "dall-e", "image",
    "allam", "compound", "orpheus", "playai", "distil-whisper",
    "audio", "vision-preview", "search", "safety", ":free",
)


@router.get("/")
async def list_models():
    """
    List available LLM models from the provider.

    Returns the current default model and all available models.
    Filters out non-text-generation models (whisper, embedding, etc.).
    Caches for 5 minutes; falls back to just the default model on error.
    """
    now = time.time()
    if _cache[1] and (now - _cache[0]) < CACHE_TTL_SECONDS:
        return {"models": _cache[1], "default": LLM_MODEL}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{LLM_BASE_URL}/models",
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()

        # OpenAI-compatible format: {"data": [{"id": "model-name", ...}]}
        raw_models = data.get("data", [])

        models = []
        for m in raw_models:
            model_id = m.get("id", "")
            # Filter out non-text models
            if any(pat in model_id.lower() for pat in _EXCLUDE_PATTERNS):
                continue
            models.append({
                "id": model_id,
                "name": model_id,
                "owned_by": m.get("owned_by", ""),
            })

        models.sort(key=lambda m: m["id"])

        _cache[0] = now
        _cache[1] = models
        return {"models": models, "default": LLM_MODEL}

    except Exception as e:
        logger.warning(f"Failed to fetch models from {LLM_BASE_URL}: {e}")
        # Fallback: return just the current default so the UI always works
        fallback = [{"id": LLM_MODEL, "name": LLM_MODEL, "owned_by": ""}]
        return {"models": fallback, "default": LLM_MODEL}
