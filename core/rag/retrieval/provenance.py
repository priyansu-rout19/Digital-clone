import logging
from typing import Optional
import psycopg

from core.rag.ingestion.embedder import get_embedder

logger = logging.getLogger(__name__)


def query_teaching_graph(
    sub_queries: list[str],
    clone_id: str,
    access_tiers: list[str],
    db_url: str,
    max_depth: int = 3,
) -> list[dict]:
    try:
        if not sub_queries:
            logger.warning("query_teaching_graph called with empty sub_queries")
            return []

        if not access_tiers:
            logger.warning("query_teaching_graph called with empty access_tiers")
            return []

        seed_teaching_ids = _find_seed_teachings(
            sub_queries[0], clone_id, access_tiers, db_url
        )

        if not seed_teaching_ids:
            logger.info(
                f"No seed teachings found for clone {clone_id} "
                f"matching tiers {access_tiers}"
            )
            return []

        logger.info(f"Found {len(seed_teaching_ids)} seed teachings")

        provenance_results = _traverse_teaching_graph(
            seed_teaching_ids, clone_id, access_tiers, db_url, max_depth
        )

        logger.info(
            f"Graph traversal returned {len(provenance_results)} related teachings"
        )
        return provenance_results

    except Exception as e:
        logger.error(f"Error in query_teaching_graph: {str(e)}")
        raise ValueError(f"Provenance graph query failed: {str(e)}")


def _find_seed_teachings(
    query_text: str,
    clone_id: str,
    access_tiers: list[str],
    db_url: str,
    limit: int = 5,
) -> list[str]:
    try:
        embedder = get_embedder()
        query_vector = embedder.embed([query_text])[0]
        logger.debug(f"Embedded query text to {len(query_vector)}-d vector")

        doc_ids = []
        try:
            vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT doc_id
                        FROM document_chunks
                        WHERE clone_id = %s
                          AND access_tier = ANY(%s)
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (clone_id, access_tiers, vector_str, limit),
                    )
                    doc_ids = [row[0] for row in cur.fetchall()]
                    logger.debug(f"Found {len(doc_ids)} documents via vector search")

        except Exception as e:
            raise ValueError(f"Vector search failed: {str(e)}")

        if not doc_ids:
            return []

        seed_teaching_ids = []
        try:
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    for doc_id in doc_ids:
                        cur.execute(
                            """
                            SELECT id FROM teachings
                            WHERE clone_id = %s
                              AND access_tier = ANY(%s)
                              AND chunk_refs @> %s::jsonb
                            """,
                            (clone_id, access_tiers, f'[{{"doc_id": "{doc_id}"}}]'),
                        )
                        seed_teaching_ids.extend([row[0] for row in cur.fetchall()])

                logger.debug(
                    f"Found {len(seed_teaching_ids)} teachings "
                    f"referencing {len(doc_ids)} documents"
                )

        except Exception as e:
            raise ValueError(f"Teaching lookup failed: {str(e)}")

        return seed_teaching_ids

    except Exception as e:
        logger.error(f"Error finding seed teachings: {str(e)}")
        raise


def _traverse_teaching_graph(
    seed_teaching_ids: list[str],
    clone_id: str,
    access_tiers: list[str],
    db_url: str,
    max_depth: int = 3,
) -> list[dict]:
    try:
        if not seed_teaching_ids:
            return []

        seed_ids = list(set(seed_teaching_ids))

        results = []
        try:
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    query = """
                    WITH RECURSIVE chain AS (
                        -- Base: forward edges from seeds
                        SELECT to_teaching_id AS id,
                               from_teaching_id AS source,
                               1 AS depth,
                               ARRAY[from_teaching_id::text,
                                     to_teaching_id::text] AS path
                        FROM teaching_relations
                        WHERE from_teaching_id = ANY(%s)

                        UNION

                        -- Base: reverse edges from seeds
                        SELECT from_teaching_id AS id,
                               to_teaching_id AS source,
                               1 AS depth,
                               ARRAY[to_teaching_id::text,
                                     from_teaching_id::text] AS path
                        FROM teaching_relations
                        WHERE to_teaching_id = ANY(%s)

                        UNION ALL

                        -- Recursive: forward (with cycle guard)
                        SELECT tr.to_teaching_id,
                               c.source,
                               c.depth + 1,
                               c.path || tr.to_teaching_id::text
                        FROM teaching_relations tr
                        JOIN chain c ON tr.from_teaching_id = c.id
                        WHERE c.depth < %s
                          AND NOT tr.to_teaching_id::text = ANY(c.path)

                        UNION ALL

                        -- Recursive: reverse (with cycle guard)
                        SELECT tr.from_teaching_id,
                               c.source,
                               c.depth + 1,
                               c.path || tr.from_teaching_id::text
                        FROM teaching_relations tr
                        JOIN chain c ON tr.to_teaching_id = c.id
                        WHERE c.depth < %s
                          AND NOT tr.from_teaching_id::text = ANY(c.path)
                    )
                    SELECT DISTINCT ON (source, id)
                        source AS teaching_id,
                        id AS related_teaching_id,
                        array_to_string(path, ' \u2192 ') AS path
                    FROM chain
                    WHERE id IN (
                        SELECT id FROM teachings
                        WHERE clone_id = %s
                          AND access_tier = ANY(%s)
                    )
                      AND NOT id = ANY(%s)
                    ORDER BY source, id
                    """

                    cur.execute(query, (seed_ids, seed_ids, max_depth, max_depth, clone_id, access_tiers, seed_ids))
                    rows = cur.fetchall()

                    results = [
                        {
                            "teaching_id": str(row[0]),
                            "related_teaching_id": str(row[1]),
                            "path": row[2],
                        }
                        for row in rows
                    ]

                    logger.debug(f"Recursive CTE returned {len(results)} results")

        except Exception as e:
            raise ValueError(f"Recursive CTE execution failed: {str(e)}")

        return results

    except Exception as e:
        logger.error(f"Error traversing teaching graph: {str(e)}")
        raise
