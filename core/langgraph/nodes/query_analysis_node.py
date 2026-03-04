"""
Query Analysis Node

Classifies user intent, decomposes complex queries into sub-queries,
determines access tier, and estimates token budget — all via a single LLM call.
"""

import json
from typing import TypedDict
from core.llm import get_llm

DEFAULT_TOKEN_BUDGET = 2000


def query_analysis(state: TypedDict) -> TypedDict:
    """
    Analyze the user query to extract intent, sub-queries, and token budget.

    Uses a single LLM call to classify intent, decompose the query, and
    estimate how many tokens the response context window needs.

    Intent classes: factual | synthesis | opinion | temporal | exploratory
    Token budget: LLM estimates based on query complexity (range 1000-4000).

    Input state keys: query_text
    Output state keys: sub_queries, intent_class, access_tier, token_budget
    """

    query = state.get("query_text", "")

    if not query:
        return {
            **state,
            "intent_class": "exploratory",
            "sub_queries": [],
            "token_budget": DEFAULT_TOKEN_BUDGET,
        }

    llm = get_llm(temperature=0.0)

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

Return JSON only, no other text:
{"intent": "<class>", "sub_queries": ["...", "..."], "token_budget": <number>}

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

        # Clamp token_budget to reasonable range
        token_budget = max(1000, min(4000, int(token_budget)))

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

    return {
        **state,
        "intent_class": intent,
        "sub_queries": sub_queries,
        "token_budget": token_budget,
    }
