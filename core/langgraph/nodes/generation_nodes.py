"""
Generation Nodes (3 nodes)

LLM-based response generation, citation verification, and confidence scoring.
"""

from typing import TypedDict
from core.llm import get_llm
from core.models.clone_profile import CloneProfile, GenerationMode
from core.prompts import interpretive_generator_prompt, MIRROR_ONLY_GENERATOR_PROMPT


def make_in_persona_generator(profile: CloneProfile):
    """
    Factory function that creates an in_persona_generator node with profile captured.

    The profile determines:
    - System prompt (clone persona, display name, bio)
    - Generation mode (interpretive vs mirror_only)
    - Temperature (higher for creative interpretations)

    Returns:
        A node function (state: TypedDict) -> TypedDict
    """

    def in_persona_generator(state: TypedDict) -> TypedDict:
        """
        Generate response using the clone's persona and assembled context.

        Uses LLM to synthesize a response grounded in the assembled context.
        Behavior depends on profile.generation_mode:
        - interpretive: LLM synthesizes frameworks, applies persona
        - mirror_only: LLM constructs response from direct quotes only

        Input: assembled_context, user_memory, query_text
        Output: raw_response
        """

        query = state.get("query_text", "")
        context = state.get("assembled_context", "")
        memory = state.get("user_memory", "")
        history = state.get("conversation_history", "")

        # Build system prompt based on generation mode (prompts live in core/prompts/registry.py)
        if profile.generation_mode == GenerationMode.interpretive:
            system_prompt = interpretive_generator_prompt(profile.display_name, profile.bio)
        else:  # mirror_only
            system_prompt = MIRROR_ONLY_GENERATOR_PROMPT

        # Build user message
        user_message = f"Question: {query}\n"
        if history:
            user_message += f"\n{history}\n"
        if context:
            user_message += f"\nContext:\n{context}\n"
        if memory:
            user_message += f"\nRelevant context from memory:\n{memory}\n"
        if context:
            user_message += "\nRemember: cite sources using [1], [2], etc.\n"
        user_message += "\nAnswer:"

        # Call LLM: temperature 0.0 for mirror_only (deterministic quotes), 0.7 for interpretive
        # Response length adapts to question complexity (LLM-estimated in query_analysis)
        temp = 0.0 if profile.generation_mode == GenerationMode.mirror_only else 0.7
        response_tokens = state.get("response_tokens", 500)
        llm = get_llm(temperature=temp, max_tokens=response_tokens, model=state.get("model_override") or None)

        try:
            response = llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ])
            raw = response.content.strip()
        except Exception as e:
            # Fallback on error
            raw = f"I encountered an issue processing your question: {str(e)}"

        return {
            **state,
            "raw_response": raw,
        }

    return in_persona_generator


def citation_verifier(state: TypedDict) -> TypedDict:
    """
    Verify that claimed citations actually appear in retrieved passages.

    Parses [N] citation markers from LLM response, cross-references against
    retrieved_passages, and builds cited_sources list. Catches hallucinated
    source IDs (LLM cites [5] when only 3 passages retrieved).

    Input: raw_response, retrieved_passages
    Output: verified_response, cited_sources
    """
    import re

    raw = state.get("raw_response", "")
    passages = state.get("retrieved_passages", [])

    if not passages:
        return {**state, "verified_response": raw, "cited_sources": []}

    # Parse [N] markers from LLM response (1-indexed, matching context_assembler numbering)
    cited_indices = set(int(m) for m in re.findall(r'\[(\d+)\]', raw))

    # Cross-reference against retrieved_passages (convert to 0-indexed)
    cited_sources = []
    for idx in sorted(cited_indices):
        passage_index = idx - 1
        if 0 <= passage_index < len(passages):
            p = passages[passage_index]
            cited_sources.append({
                # Frontend-facing fields (match CitedSource interface)
                "source": p.get("source_type", "unknown"),
                "chunk_text": p.get("passage", ""),
                "score": state.get("retrieval_confidence", 0.0),
                # Provenance fields (Sacred Archive requires these)
                "date": p.get("date"),
                "location": p.get("location"),
                "event": p.get("event"),
                "verifier": p.get("verifier"),
                "source_title": p.get("source_title"),
                # Internal fields for logging/debugging
                "doc_id": p.get("doc_id", "unknown"),
                "chunk_id": p.get("chunk_id", "unknown"),
            })

    # Strip [N] markers from displayed text — citations shown as cards, not inline brackets
    clean_response = re.sub(r'\s*\[\d+\]', '', raw).strip()

    return {
        **state,
        "verified_response": clean_response,
        "cited_sources": cited_sources,
    }


def confidence_scorer(state: TypedDict) -> TypedDict:
    """
    Score overall response quality using multiple signals (0.0-1.0).

    Combines 4 independent factors instead of relying on LLM self-evaluation
    (LLMs are overconfident in 84%+ of scenarios — arXiv:2508.06225).

    Factors:
    - Retrieval confidence (0.35): how relevant were the retrieved passages?
    - Citation coverage (0.25): what fraction of passages were actually cited?
    - Response grounding (0.25): how much of the response comes from context?
    - Passage count (0.15): did we find enough source material?

    Input: retrieval_confidence, cited_sources, retrieved_passages,
           verified_response, assembled_context
    Output: final_confidence (float 0.0-1.0)
    """

    response = state.get("verified_response", "")

    if not response:
        return {**state, "final_confidence": 0.0}

    # Factor 1: Retrieval confidence (from vector search / reranker)
    retrieval_confidence = state.get("retrieval_confidence", 0.0)

    # Factor 2: Citation coverage — what fraction of passages were cited?
    passages = state.get("retrieved_passages", [])
    cited_sources = state.get("cited_sources", [])
    if passages:
        citation_coverage = min(len(cited_sources) / max(len(passages), 1), 1.0)
    else:
        citation_coverage = 0.0

    # Factor 3: Response grounding — lexical overlap between response and context
    # Include conversation history as valid grounding source for multi-turn queries
    context = state.get("assembled_context", "")
    history = state.get("conversation_history", "")
    if history:
        context = context + "\n" + history
    response_grounding = _compute_grounding_score(response, context)

    # Factor 4: Passage count factor — did we find enough material?
    passage_count_factor = min(len(passages) / 3.0, 1.0)

    # Weighted combination
    final_confidence = (
        0.35 * retrieval_confidence
        + 0.25 * citation_coverage
        + 0.25 * response_grounding
        + 0.15 * passage_count_factor
    )

    # Multi-turn context bonus: follow-up responses draw on conversation history
    # as additional grounding that isn't captured by passage-only metrics.
    # Small boost (0.10) compensates for naturally lower citation_coverage in follow-ups.
    if history:
        final_confidence += 0.10

    # Clamp to [0.0, 1.0]
    final_confidence = max(0.0, min(1.0, round(final_confidence, 3)))

    return {**state, "final_confidence": final_confidence}


def _compute_grounding_score(response: str, context: str) -> float:
    """
    Measure how grounded the response is in the context via word overlap.

    Computes the fraction of meaningful response words that appear in the context.
    Filters out stop words and short tokens to focus on content words.
    Returns 0.0-1.0.
    """
    if not response or not context:
        return 0.0

    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "and", "but", "or", "nor", "not", "so", "yet", "both",
        "each", "few", "more", "most", "other", "some", "such", "no",
        "only", "own", "same", "than", "too", "very", "just", "because",
        "if", "when", "where", "how", "what", "which", "who", "whom",
        "this", "that", "these", "those", "i", "you", "he", "she", "it",
        "we", "they", "me", "him", "her", "us", "them", "my", "your",
        "his", "its", "our", "their", "about", "also", "like", "there",
    }

    response_words = {
        w.lower() for w in response.split()
        if len(w) > 2 and w.lower() not in stop_words
    }
    context_words = {
        w.lower() for w in context.split()
        if len(w) > 2 and w.lower() not in stop_words
    }

    if not response_words:
        return 0.0

    overlap = response_words & context_words
    return len(overlap) / len(response_words)
