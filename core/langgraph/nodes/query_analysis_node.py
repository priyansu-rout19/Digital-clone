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
{"intent": "<class>", "sub_queries": ["...", "..."], "token_budget": <number>, "response_tokens": <number>}

For simple questions, sub_queries is [original_query]. For complex questions, decompose into independent sub-queries."""

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Classify this query:\n{query}"},
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
