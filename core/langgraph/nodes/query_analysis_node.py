"""
Query Analysis Node

Classifies user intent, decomposes complex queries into sub-queries,
determines access tier, and estimates token budget.
"""

import json
from typing import TypedDict
from core.llm import get_llm


def query_analysis(state: TypedDict) -> TypedDict:
    """
    Analyze the user query to extract intent, access tier, and resource needs.

    Uses LLM to classify intent and decompose into sub-queries.
    Intent classes: factual | synthesis | opinion | temporal | exploratory

    Input state keys: query_text
    Output state keys: sub_queries, intent_class, access_tier, token_budget
    """

    query = state.get("query_text", "")

    if not query:
        return {
            **state,
            "intent_class": "exploratory",
            "sub_queries": [],
            "access_tier": "public",
            "token_budget": 2000,
        }

    # Call LLM to classify intent and decompose query
    llm = get_llm(temperature=0.0)  # Deterministic classification

    system_prompt = """You are a query classifier. Analyze the user question and respond with JSON.
Intent classes: factual, synthesis, opinion, temporal, exploratory.
- factual: asks for specific facts, data, information
- synthesis: asks for connections, patterns, frameworks, analysis
- opinion: asks for viewpoint, perspective, advice
- temporal: asks about time, timelines, futures, history
- exploratory: open-ended, discovery-oriented

Return JSON only, no other text:
{"intent": "<class>", "sub_queries": ["...", "..."]}

For simple questions, sub_queries is [original_query]. For complex questions, decompose into independent sub-queries."""

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Classify this query:\n{query}"},
        ])

        # Parse JSON response
        response_text = response.content.strip()
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        result = json.loads(response_text)
        intent = result.get("intent", "exploratory")
        sub_queries = result.get("sub_queries", [query])

    except (json.JSONDecodeError, KeyError, AttributeError):
        # Fallback to heuristic if LLM response can't be parsed
        if any(word in query.lower() for word in ["how", "why", "what", "explain"]):
            intent = "factual"
        elif any(word in query.lower() for word in ["future", "think", "opinion"]):
            intent = "opinion"
        elif any(word in query.lower() for word in ["time", "when", "date"]):
            intent = "temporal"
        else:
            intent = "exploratory"
        sub_queries = [query]

    # Return updated state
    return {
        **state,
        "intent_class": intent,
        "sub_queries": sub_queries,
        "access_tier": "public",  # Will be refined based on profile + user permissions
        "token_budget": 2000,  # Standard budget; would vary based on intent
    }
