"""
Generation Nodes (3 nodes)

LLM-based response generation, citation verification, and confidence scoring.
"""

from typing import TypedDict
from core.llm import get_llm
from core.models.clone_profile import CloneProfile, GenerationMode


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

        # Build system prompt based on generation mode
        if profile.generation_mode == GenerationMode.interpretive:
            system_prompt = f"""You are {profile.display_name}.

About you: {profile.bio}

You are chatting with someone who wants to learn from you. Respond naturally, like you're having a conversation — not writing an essay or giving a lecture.

Guidelines:
- Keep responses to 2-3 short paragraphs maximum
- Be conversational and direct — talk like a person, not a textbook
- Do NOT use markdown headers (##), horizontal rules (---), or numbered lists
- Use **bold** sparingly for key concepts only
- When you draw on a specific source from the context, cite it with its number like [1] or [2] — weave these naturally into your sentences
- Start with your key insight, then explain briefly
- End with something that invites further discussion"""

        else:  # mirror_only
            system_prompt = """You are a mirror of sacred teachings. Respond ONLY with direct quotes and passages from the provided context.

Guidelines:
- Respond ONLY with direct quotes from the context provided
- Do not paraphrase, interpret, or add original commentary
- Do not add your own words or analysis
- If the context does not contain a suitable quote, do not respond
- Preserve the exact wording and meaning of the source material
- After each quote, cite its source number from the context, e.g. [1]"""

        # Build user message
        user_message = f"Question: {query}\n"
        if context:
            user_message += f"\nContext:\n{context}\n"
        if memory:
            user_message += f"\nRelevant context from memory:\n{memory}\n"
        user_message += "\nAnswer:"

        # Call LLM: temperature 0.0 for mirror_only (deterministic quotes), 0.7 for interpretive
        # max_tokens=500 keeps responses conversational (~375 words, 2-3 paragraphs)
        temp = 0.0 if profile.generation_mode == GenerationMode.mirror_only else 0.7
        llm = get_llm(temperature=temp, max_tokens=500)

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
    Score how well the response answers the original question (0.0-1.0).

    Uses LLM to evaluate response quality. Lower scores trigger silence behavior
    or review queue depending on profile settings.

    Input: verified_response, query_text
    Output: final_confidence (float 0.0-1.0)
    """

    query = state.get("query_text", "")
    response = state.get("verified_response", "")

    if not response:
        return {
            **state,
            "final_confidence": 0.0,
        }

    # Call LLM to score the response
    llm = get_llm(temperature=0.0)  

    system_prompt = """You are an evaluator. On a scale of 0.0 to 1.0, how well does the response answer the question?
0.0 = doesn't answer at all
0.5 = partially answers, missing key points
1.0 = fully and thoroughly answers

Respond with ONLY a number (0.0-1.0), nothing else."""

    user_message = f"""Question: {query}

Response: {response}

Score:"""

    try:
        response_text = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]).content.strip()

        # Parse the score, handling various formats
        score_str = response_text.split()[0]  # Get first token
        confidence = float(score_str)
        # Clamp to valid range
        confidence = max(0.0, min(1.0, confidence))

    except (ValueError, IndexError, AttributeError):
        # Fallback: assume medium confidence if we have a response
        confidence = 0.5

    return {
        **state,
        "final_confidence": confidence,
    }
