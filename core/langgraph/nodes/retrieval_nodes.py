from typing import TypedDict
from core.models.clone_profile import RetrievalTier
from core.db import psycopg_url as _psycopg_url


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
            query_text=state.get("query_text", ""),
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
    Evaluate retrieval quality using reranker scores + passage count.

    When reranking is available, uses mean reranker score of top passages
    (cross-encoder scores are far more calibrated than cosine similarity).
    Falls back to passage-count heuristic when reranker scores absent.

    No LLM call — CRAG can run up to 3 times, so this must be fast.
    """
    passages = state.get("retrieved_passages", [])
    raw_confidence = state.get("retrieval_confidence", 0.0)

    if not passages:
        return {**state, "retrieval_confidence": 0.0}

    # Use reranker scores if available (set by vector_search reranking stage)
    rerank_scores = [p.get("rerank_score") for p in passages[:5] if p.get("rerank_score") is not None]
    if rerank_scores:
        mean_score = sum(rerank_scores) / len(rerank_scores)
        passage_factor = min(len(passages) / 3.0, 1.0)
        adjusted = mean_score * passage_factor
    else:
        passage_factor = min(len(passages) / 3.0, 1.0)
        adjusted = raw_confidence * passage_factor

    adjusted = max(0.0, min(1.0, round(adjusted, 3)))

    return {**state, "retrieval_confidence": adjusted}


def query_reformulator(state: TypedDict) -> TypedDict:
    """
    Reformulate the query to find DIFFERENT passages (not paraphrases).

    Key insight: paraphrased queries embed to nearly identical vectors and
    retrieve the same passages. Instead, we ask the LLM to generate queries
    that target different aspects, use domain-specific keywords, or decompose
    the question into sub-topics — strategies that actually change what gets
    retrieved.

    The reformulator now sees actual passage text so it can diagnose WHY
    the current results are insufficient and steer the search differently.
    """
    import json
    from core.llm import get_llm

    query = state.get("query_text", "")
    retry_count = state.get("retry_count", 0) + 1
    previous_passages = state.get("retrieved_passages", [])

    if not query:
        return {**state, "retry_count": retry_count}

    # Build diagnostic info from actual passages (not just source_type)
    passage_diagnostic = ""
    if previous_passages:
        passage_diagnostic = f"Retrieved {len(previous_passages)} passages but they scored low relevance.\n"
        passage_diagnostic += "Top 3 passage previews:\n"
        for i, p in enumerate(previous_passages[:3], 1):
            text_preview = p.get("passage", "")[:200].replace("\n", " ")
            score = p.get("rerank_score", "N/A")
            title = p.get("source_title", p.get("source_type", "unknown"))
            passage_diagnostic += f"  [{i}] ({title}, score={score}) {text_preview}...\n"
    else:
        passage_diagnostic = "No passages were retrieved at all."

    llm = get_llm(temperature=0.8, model=state.get("model_override") or None)

    system_prompt = """You are a search query specialist. The current search queries failed to find relevant documents. Your job is to generate DIFFERENT search strategies — not paraphrases.

IMPORTANT: Simple rephrasing (e.g., "What about X?" or "Explain X") will retrieve the SAME results because vector search treats paraphrases identically. You must change the search strategy.

Return JSON only:
{"alternatives": ["query_1", "query_2", "query_3"]}

Strategies that ACTUALLY change results:
1. Extract specific KEYWORDS and ENTITIES (names, dates, concepts) — keyword search finds different results than semantic search
2. DECOMPOSE into sub-topics — "What is X?" becomes separate queries for different aspects
3. Use DOMAIN JARGON — technical terms from the field that the corpus likely uses
4. Try the OPPOSITE angle — if asking about benefits, try searching for the specific mechanism or example
5. BROADEN or NARROW scope dramatically — if "ASEAN trade 2023" fails, try "Southeast Asian economic integration" or "Thailand-Vietnam bilateral agreement\""""

    user_message = f"""Original question: {query}

{passage_diagnostic}

The passages above were retrieved but aren't relevant enough. Generate 3 search queries using DIFFERENT strategies (not paraphrases) that might find better documents."""

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
        # Fallback: keyword extraction + broadening (not paraphrases)
        words = [w for w in query.split() if len(w) > 3]
        keyword_query = " ".join(words[:4]) if words else query
        alternatives = [
            query,
            keyword_query,
            f"{keyword_query} overview analysis",
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
