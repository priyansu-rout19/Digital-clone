"""
Query Analysis Node

Classifies user intent, decomposes complex queries into sub-queries,
determines access tier, estimates token budget, and estimates response
length — all via a single LLM call.
"""

import json
from typing import TypedDict
from core.llm import get_llm

DEFAULT_TOKEN_BUDGET = 2000
DEFAULT_RESPONSE_TOKENS = 500


def query_analysis(state: TypedDict) -> TypedDict:
    """
    Analyze the user query to extract intent, sub-queries, token budget,
    and response token limit.

    Uses a single LLM call to classify intent, decompose the query,
    estimate how many tokens the response context window needs, and
    how long the response itself should be.

    Intent classes: factual | synthesis | opinion | temporal | exploratory
    Token budget: LLM estimates based on query complexity (range 1000-4000).
    Response tokens: LLM estimates based on answer complexity (range 100-1000).

    Input state keys: query_text
    Output state keys: sub_queries, intent_class, access_tier, token_budget, response_tokens
    """

    query = state.get("query_text", "")
    history = state.get("conversation_history", "")

    if not query:
        return {
            **state,
            "intent_class": "exploratory",
            "sub_queries": [],
            "token_budget": DEFAULT_TOKEN_BUDGET,
            "response_tokens": DEFAULT_RESPONSE_TOKENS,
        }

    llm = get_llm(temperature=0.0, model=state.get("model_override") or None)

    system_prompt = """You are a query classifier. Analyze the user question and respond with JSON.

If conversation history is provided, determine if the query is a FOLLOW-UP that references
previous context (e.g., "tell me more", "what about X?", "why is that?", "what does that mean",
pronouns like "it", "that", "this" referring to prior topics).
If it IS a follow-up, rewrite it as a SELF-CONTAINED query that includes the referenced context
from the conversation history. Put the rewritten query in the "rewritten_query" field.
If it is NOT a follow-up (standalone question), set "rewritten_query" to null.

Intent classes: factual, synthesis, opinion, temporal, exploratory.
- factual: asks for specific facts, data, information
- synthesis: asks for connections, patterns, frameworks, analysis
- opinion: asks for viewpoint, perspective, advice
- temporal: asks about time, timelines, futures, history
- exploratory: open-ended, discovery-oriented

Token budget guidelines (how many tokens of retrieved context to include):
- Simple factual question (one fact) → 1000-1500
- Moderate factual or opinion question → 2000
- Complex synthesis or multi-part question → 2500-3000
- Very broad exploratory or deep analysis → 3000-4000

Response tokens guidelines (how many tokens the response should be):
- Simple factual (one fact, yes/no, a name or date) → 100-200
- Moderate question (explain, describe, give opinion) → 300-500
- Complex synthesis or multi-part question → 500-700
- Very broad exploratory or deep analysis → 700-1000

Return JSON only, no other text:
{"intent": "<class>", "sub_queries": ["...", "..."], "token_budget": <number>, "response_tokens": <number>, "rewritten_query": "<self-contained query or null>"}

IMPORTANT: If you rewrite the query, generate sub_queries that will retrieve relevant documents.
For follow-up queries, ALWAYS generate at least 2 sub_queries:
1. One sub_query using ONLY the core topic keywords from the conversation history (e.g., "ASEAN integration connectivity infrastructure"). This ensures we retrieve the SAME relevant passages that were found in the original question.
2. One sub_query combining the original topic with the new angle (e.g., "ASEAN connectivity impact on India").
DO NOT make all sub_queries about the new angle — at least one must match the original topic exactly.
For standalone (non-follow-up) questions, sub_queries is [original_query].
For complex standalone questions, decompose into independent sub-queries."""

    try:
        # Include conversation history in user message when available
        user_content = ""
        if history:
            user_content += f"{history}\n\n"
        user_content += f"Classify this query:\n{query}"

        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ])

        response_text = response.content.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        result = json.loads(response_text)
        intent = result.get("intent", "exploratory")
        sub_queries = result.get("sub_queries", [query])
        token_budget = result.get("token_budget", DEFAULT_TOKEN_BUDGET)
        response_tokens = result.get("response_tokens", DEFAULT_RESPONSE_TOKENS)
        rewritten_query = result.get("rewritten_query")

        # For follow-up queries: ensure we retrieve passages from the original topic
        if rewritten_query and history:
            # Extract the most recent user question from history as a topic anchor
            prev_queries = [
                line[len("User: "):] for line in history.split("\n")
                if line.startswith("User: ")
            ]
            # Use the rewritten query + original topic query for dual retrieval
            sub_queries = [rewritten_query]
            if prev_queries:
                sub_queries.append(prev_queries[-1])  # Most recent prior question
        elif rewritten_query and sub_queries == [query]:
            sub_queries = [rewritten_query]

        # Clamp token_budget to reasonable range
        token_budget = max(1000, min(4000, int(token_budget)))
        # Clamp response_tokens to reasonable range
        response_tokens = max(100, min(1000, int(response_tokens)))

    except (json.JSONDecodeError, KeyError, AttributeError, ValueError):
        if any(word in query.lower() for word in ["how", "why", "what", "explain"]):
            intent = "factual"
        elif any(word in query.lower() for word in ["future", "think", "opinion"]):
            intent = "opinion"
        elif any(word in query.lower() for word in ["time", "when", "date"]):
            intent = "temporal"
        else:
            intent = "exploratory"
        sub_queries = [query]
        token_budget = DEFAULT_TOKEN_BUDGET
        response_tokens = DEFAULT_RESPONSE_TOKENS

    return {
        **state,
        "intent_class": intent,
        "sub_queries": sub_queries,
        "token_budget": token_budget,
        "response_tokens": response_tokens,
    }
