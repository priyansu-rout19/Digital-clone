import logging
from typing import Optional

import psycopg
from core.rag.ingestion.embedder import get_embedder

logger = logging.getLogger(__name__)


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


def search(
    sub_queries: list[str],
    clone_id: str,
    access_tiers: list[str],
    db_url: str,
    top_k: int = 10,
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

        rrf_scores = _compute_rrf_scores(per_query_results)

        if not rrf_scores:
            return ([], 0.0)

        sorted_results = sorted(
            rrf_scores.items(), key=lambda x: x[1]["rrf_score"], reverse=True
        )[:top_k]

        retrieved_passages = []
        for chunk_id, data in sorted_results:
            row = data["chunk"]
            # Extract provenance from documents table JOIN (JSONB → dict or None)
            provenance_raw = row[7] if len(row) > 7 else None
            provenance = provenance_raw if isinstance(provenance_raw, dict) else {}
            filename_raw = row[8] if len(row) > 8 else None
            retrieved_passages.append(
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
                logger.warning(
                    f"Failed to calculate confidence for top result: {str(e)}"
                )
                retrieval_confidence = 0.0

        return (retrieved_passages, retrieval_confidence)

    except ValueError:
        raise

    except Exception as e:
        logger.error(f"Unexpected error in vector search: {str(e)}")
        raise ValueError(f"Vector search failed: {str(e)}")
