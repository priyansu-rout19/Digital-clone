"""
Persona Fidelity Scorer — Digital Clone Engine

Deterministic scorer (no LLM call) that measures how well a response
matches the clone's configured persona. Returns a score between 0.0-1.0.

4-factor weighted model (same pattern as confidence_scorer):
  - vocabulary_match (0.30): key terms from persona found in response
  - framework_usage (0.25): signature frameworks/concepts mentioned
  - domain_relevance (0.25): response stays within owned topics
  - style_adherence (0.20): response length, citation density, tone
"""

import re
from typing import Optional


def score_persona_fidelity(
    response: str,
    persona_eval: dict,
    cited_sources: Optional[list] = None,
) -> dict:
    """
    Score how well a response matches the clone's persona.

    Args:
        response: The generated response text.
        persona_eval: Dict with keys: key_vocabulary, signature_frameworks,
                      owned_topics, style_markers.
        cited_sources: Optional list of cited source dicts.

    Returns:
        {
            "persona_fidelity": float (0.0-1.0),
            "vocabulary_match": float,
            "framework_usage": float,
            "domain_relevance": float,
            "style_adherence": float,
            "details": {...}
        }
    """
    if not response or not persona_eval:
        return {
            "persona_fidelity": 0.0,
            "vocabulary_match": 0.0,
            "framework_usage": 0.0,
            "domain_relevance": 0.0,
            "style_adherence": 0.0,
            "details": {"reason": "empty response or missing persona_eval"},
        }

    response_lower = response.lower()
    response_words = set(re.findall(r'\b\w+\b', response_lower))

    # Factor 1: Vocabulary match (0.30)
    key_vocab = persona_eval.get("key_vocabulary", [])
    if key_vocab:
        matches = sum(1 for term in key_vocab if term.lower() in response_lower)
        vocab_score = min(matches / max(len(key_vocab) * 0.3, 1), 1.0)
    else:
        vocab_score = 0.5  # neutral when unconfigured

    # Factor 2: Framework usage (0.25)
    frameworks = persona_eval.get("signature_frameworks", [])
    if frameworks:
        fw_matches = sum(1 for fw in frameworks if fw.lower() in response_lower)
        framework_score = min(fw_matches / max(len(frameworks) * 0.2, 1), 1.0)
    else:
        framework_score = 0.5

    # Factor 3: Domain relevance (0.25)
    topics = persona_eval.get("owned_topics", [])
    if topics:
        topic_words = set()
        for topic in topics:
            topic_words.update(re.findall(r'\b\w+\b', topic.lower()))
        overlap = len(response_words & topic_words)
        domain_score = min(overlap / max(len(topic_words) * 0.3, 1), 1.0)
    else:
        domain_score = 0.5

    # Factor 4: Style adherence (0.20)
    style = persona_eval.get("style_markers", {})
    style_score = _compute_style_score(response, cited_sources, style)

    # Weighted combination
    fidelity = (
        0.30 * vocab_score
        + 0.25 * framework_score
        + 0.25 * domain_score
        + 0.20 * style_score
    )

    return {
        "persona_fidelity": round(fidelity, 4),
        "vocabulary_match": round(vocab_score, 4),
        "framework_usage": round(framework_score, 4),
        "domain_relevance": round(domain_score, 4),
        "style_adherence": round(style_score, 4),
        "details": {
            "vocab_terms_found": [t for t in key_vocab if t.lower() in response_lower],
            "frameworks_found": [f for f in frameworks if f.lower() in response_lower],
            "response_word_count": len(response.split()),
        },
    }


def _compute_style_score(
    response: str,
    cited_sources: Optional[list],
    style: dict,
) -> float:
    """Score style adherence based on configurable markers."""
    scores = []

    # Citation density (if expected)
    if style.get("expects_citations", False):
        citation_count = len(re.findall(r'\[\d+\]', response))
        scores.append(min(citation_count / 2, 1.0))

    # Response length range
    word_count = len(response.split())
    min_words = style.get("min_words", 50)
    max_words = style.get("max_words", 500)
    if min_words <= word_count <= max_words:
        scores.append(1.0)
    elif word_count < min_words:
        scores.append(word_count / min_words)
    else:
        scores.append(max_words / word_count)

    # Avoids forbidden patterns
    forbidden = style.get("forbidden_patterns", [])
    if forbidden:
        violations = sum(1 for p in forbidden if p.lower() in response.lower())
        scores.append(1.0 - min(violations / len(forbidden), 1.0))

    return sum(scores) / len(scores) if scores else 0.5
