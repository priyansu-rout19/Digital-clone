"""
Routing Nodes (5 nodes)

Output routing based on confidence, review requirements, and silence behavior.
Includes review queue writing, silence hedging, and voice pipeline.
"""

from typing import TypedDict


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
            "silence_triggered": True,
        }

    return soft_hedge_router


def strict_silence_router(state: TypedDict) -> TypedDict:
    """
    Mark response as requiring silence or review (Sacred Archive pattern).

    PARTIAL IMPLEMENTATION: Sets silence_triggered flag. Routing decision
    (review queue vs silence fallback) is handled by conditional edge after this node.

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

    STUB: Depends on component 03 (DB schema) for review_queue table.
    Logs that response would be queued; actual DB write deferred until DB schema done.

    Input: verified_response, cited_sources, final_confidence
    Output: (writes to DB; state unchanged)
    """

    # STUB: In production, this would:
    # 1. Insert row into review_queue table (component 03)
    # 2. Fields: clone_id, user_id, query, response, confidence, status=pending
    # 3. Notify reviewer (email, dashboard)

    response = state.get("verified_response", "")
    confidence = state.get("final_confidence", 0.0)

    # Mock: just log
    print(f"[REVIEW QUEUE] Response queued for human review. Confidence={confidence:.2f}")
    print(f"  Response preview: {response[:100]}...")

    return state


def stream_to_user(state: TypedDict) -> TypedDict:
    """
    Prepare response for streaming to user (text output).

    PARTIAL IMPLEMENTATION: Sets voice_chunks by splitting response into chunks.
    Does not actually stream; that's handled by the API layer.

    Input: verified_response (or raw_response if hedged)
    Output: voice_chunks (text segments for TTS or display)
    """

    # Use verified_response if available, else raw (e.g., hedged response)
    response_text = state.get("verified_response", "") or state.get("raw_response", "")

    # Simple chunking: split on sentences (periods)
    chunks = []
    if response_text:
        # Split into sentences for TTS chunking
        sentences = response_text.split(". ")
        for sentence in sentences:
            if sentence.strip():
                chunks.append(sentence.strip() + ".")

    return {
        **state,
        "voice_chunks": chunks,
    }


def voice_pipeline(state: TypedDict) -> TypedDict:
    """
    Generate audio output (TTS) for voice-enabled clones (ParaGPT only).

    STUB: Depends on OpenAudio TTS integration (GPU 1, ~12GB VRAM).
    Returns empty voice chunks for mock; actual TTS deferred until hardware available.

    Input: voice_chunks, profile.voice_model_ref (for ai_clone) or profile.original_recordings
    Output: (voice_chunks remain populated; actual audio bytes handled by API layer)

    Behavior per voice_mode:
    - ai_clone: Send text to OpenAudio TTS with trained voice model
    - original_only: Return links to original recording audio files
    - text_only: Skip this node entirely (handled by conditional edge)
    """

    # STUB: In production, this would:
    # 1. For ai_clone: send voice_chunks to OpenAudio TTS
    # 2. For original_only: map chunks to timestamps in original recordings
    # 3. Return audio data (or URLs) to API for streaming

    # For stub, just return voice_chunks as-is (they contain text)
    # API layer would generate actual audio or links

    return state
