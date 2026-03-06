import logging
from typing import Optional

import psycopg
from core.rag.ingestion.embedder import get_embedder

logger = logging.getLogger(__name__)

# Module-level reranker singleton (loaded once, ~34MB model)
_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        try:
            from flashrank import Ranker
            _reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", max_length=512)
            logger.info("FlashRank reranker loaded (ms-marco-MiniLM-L-12-v2)")
        except Exception as e:
            logger.warning(f"FlashRank not available, skipping reranking: {e}")
            _reranker = False  # Sentinel: tried and failed
    return _reranker if _reranker is not False else None


def _compute_rrf_scores(
    per_query_results: list[list[tuple]], k: int = 60
) -> dict[str, dict]:
    scores = {}

    for query_results in per_query_results:
        for row, rank in query_results:
            chunk_id = row[0]
            rrf = 1.0 / (k + rank)

            if chunk_id not in scores:
                scores[chunk_id] = {"chunk": row, "rrf_score": 0.0}

            scores[chunk_id]["rrf_score"] += rrf

    return scores


def _bm25_search(
    query_text: str,
    clone_id: str,
    access_tiers: list[str],
    db_url: str,
    limit: int = 15,
) -> list[tuple]:
    """
    BM25 keyword search via PostgreSQL tsvector/tsquery.

    Returns results in the same row format as vector search so they can be
    combined via RRF. BM25 finds passages by keyword frequency — fundamentally
    different from vector cosine similarity. This means reformulated queries
    with different keywords will retrieve DIFFERENT passages.
    """
    if not query_text or not clone_id or not db_url:
        return []

    try:
        # Convert natural language to tsquery (plainto_tsquery handles phrases safely)
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT dc.chunk_id, dc.doc_id, dc.passage, dc.source_type,
                           dc.access_tier, dc.date,
                           ts_rank(dc.search_vector, plainto_tsquery('english', %s)) AS bm25_score,
                           d.provenance, d.filename
                    FROM document_chunks dc
                    LEFT JOIN documents d ON dc.doc_id = d.id
                    WHERE dc.clone_id = %s
                      AND dc.access_tier = ANY(%s)
                      AND dc.search_vector IS NOT NULL
                      AND dc.search_vector @@ plainto_tsquery('english', %s)
                    ORDER BY bm25_score DESC
                    LIMIT %s
                    """,
                    (query_text, clone_id, access_tiers, query_text, limit),
                )
                rows = cur.fetchall()
                return [(row, rank) for rank, row in enumerate(rows, start=1)]

    except Exception as e:
        logger.warning(f"BM25 search failed (non-fatal, vector search continues): {e}")
        return []


def search(
    sub_queries: list[str],
    clone_id: str,
    access_tiers: list[str],
    db_url: str,
    top_k: int = 10,
    query_text: str = "",
) -> tuple[list[dict], float]:
    if not sub_queries:
        return ([], 0.0)

    if not clone_id or not access_tiers or not db_url:
        raise ValueError(
            "clone_id, access_tiers, and db_url must be provided and non-empty"
        )

    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    try:
        embedder = get_embedder()
        query_vectors = embedder.embed(sub_queries)

        if not query_vectors:
            return ([], 0.0)

        per_query_results = []

        for i, query_vector in enumerate(query_vectors):
            try:
                with psycopg.connect(db_url) as conn:
                    with conn.cursor() as cur:
                        vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

                        cur.execute(
                            """
                            SELECT dc.chunk_id, dc.doc_id, dc.passage, dc.source_type,
                                   dc.access_tier, dc.date,
                                   1 - (dc.embedding <=> %s::vector) AS similarity,
                                   d.provenance, d.filename
                            FROM document_chunks dc
                            LEFT JOIN documents d ON dc.doc_id = d.id
                            WHERE dc.clone_id = %s
                              AND dc.access_tier = ANY(%s)
                            ORDER BY dc.embedding <=> %s::vector
                            LIMIT %s
                            """,
                            (vector_str, clone_id, access_tiers, vector_str, top_k),
                        )

                        rows = cur.fetchall()

                        ranked = [(row, rank) for rank, row in enumerate(rows, start=1)]
                        per_query_results.append(ranked)

            except Exception as e:
                raise ValueError(
                    f"pgvector search failed for sub-query {i} "
                    f"(text={sub_queries[i][:50]}...): {str(e)}"
                )

        # BM25 keyword search (runs in parallel with vector results via RRF fusion)
        bm25_query = query_text or (sub_queries[0] if sub_queries else "")
        if bm25_query:
            bm25_results = _bm25_search(bm25_query, clone_id, access_tiers, db_url)
            if bm25_results:
                per_query_results.append(bm25_results)

        rrf_scores = _compute_rrf_scores(per_query_results)

        if not rrf_scores:
            return ([], 0.0)

        # Over-retrieve candidates for reranking (3x top_k, then rerank to top_k)
        candidate_limit = top_k * 3
        sorted_results = sorted(
            rrf_scores.items(), key=lambda x: x[1]["rrf_score"], reverse=True
        )[:candidate_limit]

        # Build candidate passage list
        candidates = []
        for chunk_id, data in sorted_results:
            row = data["chunk"]
            provenance_raw = row[7] if len(row) > 7 else None
            provenance = provenance_raw if isinstance(provenance_raw, dict) else {}
            filename_raw = row[8] if len(row) > 8 else None
            candidates.append(
                {
                    "chunk_id": str(row[0]),
                    "doc_id": str(row[1]),
                    "passage": row[2],
                    "source_type": row[3],
                    "access_tier": row[4],
                    "date": row[5] or provenance.get("date"),
                    "location": provenance.get("location"),
                    "event": provenance.get("event"),
                    "verifier": provenance.get("verifier"),
                    "source_title": provenance.get("title") or filename_raw,
                }
            )

        # Stage 2: Rerank candidates with cross-encoder
        reranker = _get_reranker()
        rerank_query = query_text or (sub_queries[0] if sub_queries else "")

        if reranker and candidates and rerank_query:
            try:
                from flashrank import RerankRequest

                rerank_input = [
                    {"id": i, "text": p["passage"], "meta": {"chunk_id": p["chunk_id"]}}
                    for i, p in enumerate(candidates)
                ]
                rerank_results = reranker.rerank(
                    RerankRequest(query=rerank_query, passages=rerank_input)
                )

                # Rebuild passages in reranked order, store reranker score
                reranked_passages = []
                for rr in rerank_results[:top_k]:
                    idx = rr["id"]
                    passage = candidates[idx].copy()
                    passage["rerank_score"] = round(float(rr["score"]), 4)
                    reranked_passages.append(passage)

                # Confidence = mean reranker score of top 5 (calibrated cross-encoder score)
                top_scores = [p["rerank_score"] for p in reranked_passages[:5]]
                retrieval_confidence = sum(top_scores) / len(top_scores) if top_scores else 0.0
                retrieval_confidence = max(0.0, min(1.0, round(retrieval_confidence, 3)))

                return (reranked_passages, retrieval_confidence)

            except Exception as e:
                logger.warning(f"Reranking failed, falling back to RRF order: {e}")

        # Fallback: no reranker available — use RRF order + cosine similarity confidence
        retrieved_passages = candidates[:top_k]

        retrieval_confidence = 0.0
        if retrieved_passages:
            try:
                top_chunk_id = retrieved_passages[0]["chunk_id"]
                vector_str = "[" + ",".join(str(v) for v in query_vectors[0]) + "]"

                with psycopg.connect(db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT 1 - (embedding <=> %s::vector) AS similarity
                            FROM document_chunks
                            WHERE chunk_id = %s
                            """,
                            (vector_str, top_chunk_id),
                        )
                        result = cur.fetchone()
                        if result:
                            retrieval_confidence = float(result[0])
            except Exception as e:
                logger.warning(f"Fallback confidence calc failed: {e}")

        return (retrieved_passages, retrieval_confidence)

    except ValueError:
        raise

    except Exception as e:
        logger.error(f"Unexpected error in vector search: {str(e)}")
        raise ValueError(f"Vector search failed: {str(e)}")
