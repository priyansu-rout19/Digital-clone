import logging
from typing import Optional

import psycopg

logger = logging.getLogger(__name__)


def search(
    query_text: str,
    existing_passages: list[dict],
    clone_id: str,
    db_url: str,
) -> list[dict]:

    if not existing_passages:
        return existing_passages

    try:
        doc_ids = {p.get("doc_id") for p in existing_passages if p.get("doc_id")}

        if not doc_ids:
            return existing_passages

        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, filename, pageindex_tree_path
                    FROM documents
                    WHERE id = ANY(%s)
                      AND pageindex_tree_path IS NOT NULL
                    LIMIT 5
                    """,
                    (list(doc_ids),),
                )

                docs_with_trees = cur.fetchall()

        if docs_with_trees:
            logger.info(
                f"Tier 2 tree search: Found {len(docs_with_trees)} document(s) "
                f"with PageIndex tree paths: {[d[1] for d in docs_with_trees]}. "
                f"MinIO not yet configured — stub returning existing passages unchanged. "
                f"Ready to implement in Week 3 deployment phase."
            )
        else:
            logger.debug("Tier 2 tree search: No documents with PageIndex trees found.")

        return existing_passages

    except Exception as e:
        logger.warning(f"Tier 2 tree search error (stub): {e}. Returning existing passages unchanged.")
        return existing_passages
