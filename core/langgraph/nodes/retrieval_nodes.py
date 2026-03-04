import os
from typing import TypedDict
from core.models.clone_profile import RetrievalTier


def _psycopg_url() -> str:
    """Convert SQLAlchemy DATABASE_URL to raw psycopg format."""
    return os.environ.get("DATABASE_URL", "").replace("+psycopg", "")


def provenance_graph_query(state: TypedDict) -> TypedDict:
    from core.rag.retrieval import provenance

    try:
        graph_results = provenance.query_teaching_graph(
            sub_queries=state.get("sub_queries") or [state.get("query_text", "")],
            clone_id=state.get("clone_id", ""),
            access_tiers=[state.get("access_tier", "public")],
            db_url=_psycopg_url(),
        )

        return {
            **state,
            "provenance_graph_results": graph_results,
        }

    except Exception as e:
        import logging
        logging.error(f"provenance_graph_query failed: {e}")
        return {
            **state,
            "provenance_graph_results": [],
        }


def tier1_retrieval(state: TypedDict) -> TypedDict:
    from core.rag.retrieval import vector_search

    try:
        passages, confidence = vector_search.search(
            sub_queries=state.get("sub_queries") or [state.get("query_text", "")],
            clone_id=state.get("clone_id", ""),
            access_tiers=[state.get("access_tier", "public")],
            db_url=_psycopg_url(),
        )

        return {
            **state,
            "retrieved_passages": passages,
            "retrieval_confidence": confidence,
        }

    except Exception as e:
        import logging
        logging.error(f"tier1_retrieval failed: {e}")
        return {
            **state,
            "retrieved_passages": [],
            "retrieval_confidence": 0.0,
        }


def crag_evaluator(state: TypedDict) -> TypedDict:
    """
    Evaluate retrieval quality and adjust confidence before routing.

    Checks passage count and adjusts the raw vector similarity confidence.
    Few passages (< 3) get penalized — a single passage with 0.9 similarity
    might still be the wrong topic. The after_crag() routing function then
    uses this adjusted confidence to decide: proceed or retry via CRAG loop.

    No LLM call here — CRAG can run up to 3 times in the retry loop,
    so we keep this node fast (pure math).
    """
    passages = state.get("retrieved_passages", [])
    raw_confidence = state.get("retrieval_confidence", 0.0)

    if not passages:
        return {**state, "retrieval_confidence": 0.0}

    # Penalize when few passages retrieved (< 3 passages = partial credit)
    passage_count_factor = min(len(passages) / 3.0, 1.0)
    adjusted = raw_confidence * passage_count_factor
    adjusted = max(0.0, min(1.0, adjusted))

    return {**state, "retrieval_confidence": adjusted}


def query_reformulator(state: TypedDict) -> TypedDict:
    import json
    from core.llm import get_llm

    query = state.get("query_text", "")
    retry_count = state.get("retry_count", 0) + 1
    previous_passages = state.get("retrieved_passages", [])

    if not query:
        return {**state, "retry_count": retry_count}

    if previous_passages:
        passage_summary = f"Got {len(previous_passages)} passages but with low confidence. Topics included: "
        topics = set()
        for p in previous_passages[:3]:  # Sample first 3
            topics.add(p.get("source_type", "unknown")[:30])
        passage_summary += ", ".join(topics)
    else:
        passage_summary = "Retrieved no passages with sufficient confidence."

    llm = get_llm(temperature=0.7)

    system_prompt = """You are a query reformulation expert. Given a query that didn't produce good retrieval results, suggest alternative phrasings that might work better.

Return JSON only:
{"alternatives": ["rephrased_query_1", "rephrased_query_2", "rephrased_query_3"]}

Strategies:
- Try different terminology (synonyms, related concepts)
- Decompose complex questions
- Use specific keywords from the domain
- Ask more directly or more broadly depending on the original"""

    user_message = f"""Original query: {query}

Previous retrieval result: {passage_summary}

Suggest 1-3 alternative phrasings that might retrieve better results."""

    try:
        response_text = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]).content.strip()

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        result = json.loads(response_text)
        alternatives = result.get("alternatives", [query])

    except (json.JSONDecodeError, KeyError, AttributeError):
        alternatives = [
            query,
            f"What about {query.lower().replace('?', '')}?",
            f"Explain {query.lower().replace('?', '')}",
        ]

    return {
        **state,
        "sub_queries": alternatives,
        "retry_count": retry_count,
    }


def tier2_tree_search(state: TypedDict) -> TypedDict:
    from core.rag.retrieval import tree_search

    try:
        augmented_passages = tree_search.search(
            query_text=state.get("query_text", ""),
            existing_passages=state.get("retrieved_passages", []),
            clone_id=state.get("clone_id", ""),
            db_url=_psycopg_url(),
        )

        return {
            **state,
            "retrieved_passages": augmented_passages,
        }

    except Exception as e:
        import logging
        logging.error(f"tier2_tree_search failed: {e}")
        return state  # Return unchanged on error
