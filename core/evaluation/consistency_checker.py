"""
Consistency Checker — Digital Clone Engine

Detects contradictions between the current response and conversation history.
Uses keyword overlap + negation detection (no LLM call).

Returns a score (1.0 = consistent, 0.0 = contradictory) and details.
"""

import re
from typing import Optional

# Common negation patterns
NEGATION_WORDS = {
    "not", "no", "never", "neither", "nor", "none", "nothing",
    "nowhere", "cannot", "can't", "don't", "doesn't", "didn't",
    "won't", "wouldn't", "shouldn't", "isn't", "aren't", "wasn't",
    "weren't", "haven't", "hasn't", "hadn't",
}

# Words that signal opposition
CONTRAST_MARKERS = {
    "however", "but", "although", "whereas", "contrary", "opposite",
    "instead", "rather", "unlike", "disagree", "incorrect", "wrong",
    "false", "mistake",
}


def check_consistency(
    current_response: str,
    history: list[dict],
    min_overlap_threshold: float = 0.15,
) -> dict:
    """
    Check for contradictions between current response and conversation history.

    Args:
        current_response: The newly generated response text.
        history: List of {"query_text": str, "response_text": str} dicts.
        min_overlap_threshold: Minimum topic overlap to consider responses comparable.

    Returns:
        {
            "consistency_score": float (1.0 = consistent, 0.0 = contradictory),
            "contradictions": list of dicts with details,
            "comparisons_made": int
        }
    """
    if not current_response or not history:
        return {
            "consistency_score": 1.0,
            "contradictions": [],
            "comparisons_made": 0,
        }

    current_claims = _extract_claims(current_response)
    contradictions = []
    comparisons = 0

    for entry in history:
        prev_response = entry.get("response_text", "")
        if not prev_response:
            continue

        # Check topic overlap — only compare responses about similar topics
        overlap = _topic_overlap(current_response, prev_response)
        if overlap < min_overlap_threshold:
            continue

        comparisons += 1
        prev_claims = _extract_claims(prev_response)

        # Check for negation contradictions
        for curr_claim in current_claims:
            for prev_claim in prev_claims:
                contradiction = _detect_contradiction(curr_claim, prev_claim)
                if contradiction:
                    contradictions.append({
                        "current_claim": curr_claim["text"],
                        "previous_claim": prev_claim["text"],
                        "type": contradiction["type"],
                        "confidence": contradiction["confidence"],
                    })

    # Score: 1.0 if no contradictions, decreasing with severity
    if not contradictions:
        score = 1.0
    else:
        avg_confidence = sum(c["confidence"] for c in contradictions) / len(contradictions)
        score = max(0.0, 1.0 - avg_confidence * len(contradictions) * 0.2)

    return {
        "consistency_score": round(score, 4),
        "contradictions": contradictions[:5],  # limit output
        "comparisons_made": comparisons,
    }


def _extract_claims(text: str) -> list[dict]:
    """Extract simple factual claims (sentences) from text."""
    sentences = re.split(r'[.!?]+', text)
    claims = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent.split()) < 5:
            continue
        words = set(re.findall(r'\b\w+\b', sent.lower()))
        has_negation = bool(words & NEGATION_WORDS)
        claims.append({
            "text": sent,
            "words": words,
            "negated": has_negation,
        })
    return claims


def _topic_overlap(text_a: str, text_b: str) -> float:
    """Compute word overlap ratio between two texts (Jaccard-like)."""
    words_a = set(re.findall(r'\b\w{4,}\b', text_a.lower()))
    words_b = set(re.findall(r'\b\w{4,}\b', text_b.lower()))
    if not words_a or not words_b:
        return 0.0
    intersection = len(words_a & words_b)
    union = len(words_a | words_b)
    return intersection / union if union else 0.0


def _detect_contradiction(
    claim_a: dict,
    claim_b: dict,
) -> Optional[dict]:
    """Detect if two claims contradict each other."""
    # Need sufficient word overlap to be about the same topic
    common = claim_a["words"] & claim_b["words"] - NEGATION_WORDS - CONTRAST_MARKERS
    if len(common) < 3:
        return None

    # Negation flip: one claim negated, the other not, about same topic
    if claim_a["negated"] != claim_b["negated"]:
        return {
            "type": "negation_flip",
            "confidence": min(len(common) / 5, 0.9),
        }

    # Contrast markers in one of the claims referencing the other's topic
    a_contrasts = claim_a["words"] & CONTRAST_MARKERS
    b_contrasts = claim_b["words"] & CONTRAST_MARKERS
    if (a_contrasts or b_contrasts) and len(common) >= 4:
        return {
            "type": "contrast_marker",
            "confidence": min(len(common) / 6, 0.7),
        }

    return None
