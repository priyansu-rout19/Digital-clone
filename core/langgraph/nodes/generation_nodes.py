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

Your role: Synthesize your knowledge and frameworks to answer questions. Reference your past work and apply your analytical lenses. Be direct, insightful, and grounded in evidence.

Guidelines:
- Answer the question directly and thoroughly
- Apply your unique perspective and frameworks
- Reference relevant concepts or works when appropriate
- Be confident but acknowledge limitations
- Keep responses conversational and engaging"""

        else:  # mirror_only
            system_prompt = """You are a mirror of sacred teachings. Respond ONLY with direct quotes and passages from the provided context.

Guidelines:
- Respond ONLY with direct quotes from the context provided
- Do not paraphrase, interpret, or add original commentary
- Do not add your own words or analysis
- If the context does not contain a suitable quote, do not respond
- Preserve the exact wording and meaning of the source material"""

        # Build user message
        user_message = f"Question: {query}\n"
        if context:
            user_message += f"\nContext:\n{context}\n"
        if memory:
            user_message += f"\nRelevant context from memory:\n{memory}\n"
        user_message += "\nAnswer:"

        # Call LLM with appropriate temperature
        llm = get_llm(temperature=0.7)

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

    STUB: For now, just passes through the response. In production, would:
    1. Parse any citation references in raw_response
    2. Cross-check each against retrieved_passages
    3. Mark unverifiable citations
    4. Extract valid source references

    Input: raw_response, retrieved_passages
    Output: verified_response, cited_sources
    """

    raw = state.get("raw_response", "")

    return {
        **state,
        "verified_response": raw,  # For now, verified = raw (no real passages to check)
        "cited_sources": [],  # No actual verification yet
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
