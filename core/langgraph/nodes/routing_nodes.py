"""
Routing Nodes (5 nodes)

Output routing based on confidence, review requirements, and silence behavior.
Includes review queue writing, silence hedging, and voice pipeline.
"""

import json
import logging
import re
import uuid
from typing import TypedDict

import psycopg

from core.db import psycopg_url as _psycopg_url

logger = logging.getLogger(__name__)


def make_soft_hedge_router(profile):
    """
    Factory function that creates a soft_hedge_router node with profile captured.

    The profile provides the silence_message to return when confidence is low.

    Args:
        profile: CloneProfile instance (for ParaGPT with soft_hedge behavior)

    Returns:
        A node function (state: TypedDict) -> TypedDict
    """

    def soft_hedge_router(state: TypedDict) -> TypedDict:
        """
        Generate a hedged response when confidence is low (ParaGPT only).

        Returns the profile's configured silence_message to gracefully handle
        low-confidence situations without completely refusing to respond.

        Input: (state from confidence_scorer)
        Output: raw_response (overwritten with hedge), silence_triggered
        """

        return {
            **state,
            "raw_response": profile.silence_message,
            "verified_response": profile.silence_message,
            "silence_triggered": True,
        }

    return soft_hedge_router


def strict_silence_router(state: TypedDict) -> TypedDict:
    """
    Mark response as requiring silence or review (Sacred Archive pattern).

    Sets silence_triggered flag. Routing decision (review queue vs silence
    fallback) is handled by conditional edge after this node.

    Input: (state from confidence_scorer)
    Output: silence_triggered
    """

    # Routing logic is in the conditional edge after this node:
    # - If review_required, goes to review_queue_writer
    # - Else, goes to stream_to_user (with silence fallback message)

    return {
        **state,
        "silence_triggered": True,
    }


def review_queue_writer(state: TypedDict) -> TypedDict:
    """
    Write response to review queue for human approval (Sacred Archive, high-review ParaGPT).

    Inserts a row into the review_queue table with status='pending'.
    The review API (GET /review/{slug}, PATCH /review/{id}) reads from this table.

    Input: clone_id, user_id, query_text, verified_response, cited_sources, final_confidence
    Output: (writes to DB; state unchanged)
    """

    clone_id = state.get("clone_id", "")
    user_id = state.get("user_id")
    query_text = state.get("query_text", "")
    response_text = state.get("verified_response", "") or state.get("raw_response", "")
    cited_sources = state.get("cited_sources", [])
    confidence = state.get("final_confidence", 0.0)

    if not clone_id or not response_text:
        logger.warning("review_queue_writer: missing clone_id or response_text, skipping DB write")
        return state

    db_url = _psycopg_url()
    if not db_url:
        logger.error("review_queue_writer: DATABASE_URL not set, cannot write to review queue")
        return state

    # "anonymous" is not a valid UUID — set to None (column is nullable)
    user_id_val = None
    if user_id and user_id != "anonymous":
        try:
            uuid.UUID(user_id)  # validate it's a real UUID
            user_id_val = user_id
        except ValueError:
            user_id_val = None

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO review_queue
                        (id, clone_id, user_id, query_text, response_text,
                         cited_sources, confidence_score, status)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, 'pending')
                    """,
                    (
                        str(uuid.uuid4()),
                        clone_id,
                        user_id_val,
                        query_text,
                        response_text,
                        json.dumps(cited_sources) if cited_sources else None,
                        confidence,
                    ),
                )
            conn.commit()
        logger.info(f"[REVIEW QUEUE] Response queued for human review. confidence={confidence:.2f}")
    except Exception as e:
        logger.error(f"review_queue_writer DB write failed: {e}")

    return state


def stream_to_user(state: TypedDict) -> TypedDict:
    """
    Prepare response for streaming to user (text output).

    Uses LLM to split response into proper sentences (handles abbreviations,
    decimals, dialogue, etc. correctly). Falls back to naive splitting on error.

    Input: verified_response (or raw_response if hedged)
    Output: voice_chunks (text segments for TTS or display)
    """
    from core.llm import get_llm

    response_text = state.get("verified_response", "") or state.get("raw_response", "")

    if not response_text:
        return {**state, "voice_chunks": []}

    # Use LLM for context-aware sentence splitting
    try:
        llm = get_llm(temperature=0.0)
        result = llm.invoke([
            {"role": "system", "content": (
                "Split the following text into individual sentences. "
                "Handle abbreviations (Dr., Mr., U.S., etc.), decimal numbers, "
                "and other tricky punctuation correctly. "
                "Return a JSON array of strings, each being one sentence. "
                "Return JSON only, no other text."
            )},
            {"role": "user", "content": response_text},
        ])

        text = result.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        sentences = json.loads(text)
        if isinstance(sentences, list) and all(isinstance(s, str) for s in sentences):
            chunks = [s.strip() for s in sentences if s.strip()]
        else:
            chunks = _naive_split(response_text)
    except Exception:
        logger.debug("LLM sentence splitting failed, using naive fallback")
        chunks = _naive_split(response_text)

    return {**state, "voice_chunks": chunks}


def _naive_split(text: str) -> list[str]:
    """Fallback sentence splitting using regex on sentence-ending punctuation."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def make_voice_pipeline(profile):
    """
    Factory function that creates a voice_pipeline node with profile captured.

    Uses edge-tts (Microsoft Edge TTS) for ai_clone mode — completely free,
    no API key needed, good quality voices with natural intonation.

    Behavior per voice_mode:
    - ai_clone: Generate MP3 audio via edge-tts, store as base64 in state
    - original_only: Stub (needs recording timestamp mapping not yet in data model)
    - text_only: Never reached (conditional edge skips this node)
    """

    def voice_pipeline(state: TypedDict) -> TypedDict:
        voice_chunks = state.get("voice_chunks", [])

        if not voice_chunks:
            return state

        if profile.voice_mode.value == "ai_clone":
            return _generate_tts_audio(state, voice_chunks)
        elif profile.voice_mode.value == "original_only":
            logger.info("voice_pipeline: original_only mode — audio linking not yet implemented")
            return state
        else:
            return state

    return voice_pipeline


def _generate_tts_audio(state: TypedDict, voice_chunks: list[str]) -> TypedDict:
    """
    Generate TTS audio using edge-tts (Microsoft Edge voices).

    edge-tts is async, so we bridge to sync via asyncio. Returns
    base64-encoded MP3 audio in state for the API layer to serve.
    """
    import asyncio
    import base64
    import io

    try:
        import edge_tts
    except ImportError:
        logger.error("edge-tts not installed. Run: pip install edge-tts")
        return state

    full_text = " ".join(voice_chunks)
    if not full_text.strip():
        return state

    # Default to a natural-sounding English voice.
    # Can be made configurable via profile.voice_model_ref later.
    voice = "en-US-GuyNeural"

    try:
        # edge-tts is async — bridge to sync context
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already inside an event loop (e.g., FastAPI) — use nest_asyncio or thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                audio_bytes = pool.submit(
                    asyncio.run, _run_edge_tts(full_text, voice)
                ).result(timeout=30)
        else:
            audio_bytes = asyncio.run(_run_edge_tts(full_text, voice))

        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            logger.info(f"TTS generated {len(audio_bytes)} bytes of MP3 audio")
            return {
                **state,
                "audio_base64": audio_b64,
                "audio_format": "mp3",
            }
        else:
            logger.warning("edge-tts returned empty audio")
            return state

    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        return state


async def _run_edge_tts(text: str, voice: str) -> bytes:
    """Async helper to run edge-tts and collect MP3 bytes."""
    import io
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    audio_buffer = io.BytesIO()

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])

    return audio_buffer.getvalue()
