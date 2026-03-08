"""
Query Analysis Node

Classifies user intent, decomposes complex queries into sub-queries,
determines access tier, estimates token budget, and estimates response
length — all via a single LLM call.
"""

import json
from typing import TypedDict
from core.llm import get_llm
from core.prompts import QUERY_CLASSIFIER_PROMPT

DEFAULT_TOKEN_BUDGET = 2000
DEFAULT_RESPONSE_TOKENS = 500


def query_analysis(state: TypedDict) -> TypedDict:
    """
    Analyze the user query to extract intent, sub-queries, token budget,
    and response token limit.

    Uses a single LLM call to classify intent, decompose the query,
    estimate how many tokens the response context window needs, and
    how long the response itself should be.

    Intent classes: conversational | factual | synthesis | opinion | temporal | exploratory
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

    llm = get_llm(temperature=0.0, max_tokens=512, model=state.get("model_override") or None)

    system_prompt = QUERY_CLASSIFIER_PROMPT

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
        # Self-referential queries — need conversation history, not corpus
        self_ref_patterns = ["my name", "my country", "about me", "remember me",
                             "who am i", "did i say", "did i tell", "i told you",
                             "where am i from", "where i am from"]
        query_lower = query.lower()
        if any(p in query_lower for p in self_ref_patterns):
            intent = "conversational"
            sub_queries = []
            token_budget = 0
            response_tokens = 150
        elif (greeting_words := {"hi", "hello", "hey", "hii", "namaste", "good morning",
                          "good evening", "thanks", "thank you", "bye", "goodbye",
                          "yo", "sup", "hola", "greetings"}) and set(query_lower.split()) & greeting_words and not any(
            w in query_lower for w in ["how", "why", "what", "explain", "tell"]
        ):
            intent = "conversational"
            sub_queries = []
            token_budget = 0
            response_tokens = 150
        elif any(word in query.lower() for word in ["how", "why", "what", "explain"]):
            intent = "factual"
            sub_queries = [query]
            token_budget = DEFAULT_TOKEN_BUDGET
            response_tokens = DEFAULT_RESPONSE_TOKENS
        elif any(word in query.lower() for word in ["future", "think", "opinion"]):
            intent = "opinion"
            sub_queries = [query]
            token_budget = DEFAULT_TOKEN_BUDGET
            response_tokens = DEFAULT_RESPONSE_TOKENS
        elif any(word in query.lower() for word in ["time", "when", "date"]):
            intent = "temporal"
            sub_queries = [query]
            token_budget = DEFAULT_TOKEN_BUDGET
            response_tokens = DEFAULT_RESPONSE_TOKENS
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
        "retry_count": 0,  # Bug fix 5: reset per query so stale count doesn't block CRAG retries
    }
