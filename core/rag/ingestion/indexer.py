import psycopg
from pgvector.psycopg import register_vector


def index_chunks(
    doc_id: str,
    clone_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    source_type: str,
    access_tier: str,
    date: str | None,
    db_url: str,
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Chunk count mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
        )
    if not chunks:
        return 0
    for i, emb in enumerate(embeddings):
        if len(emb) != 1024:
            raise ValueError(
                f"Embedding {i} has {len(emb)} dimensions, expected 1024 (Google Gemini, truncated)"
            )
    try:
        with psycopg.connect(db_url) as conn:
            register_vector(conn)
            rows = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{doc_id}_{i:04d}"
                rows.append(
                    (
                        doc_id,
                        clone_id,
                        i,
                        chunk_id,
                        chunk,
                        source_type,
                        access_tier,
                        date,
                        embedding,
                    )
                )
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO document_chunks (
                        doc_id, clone_id, chunk_index, chunk_id, passage,
                        source_type, access_tier, date, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        passage = EXCLUDED.passage,
                        embedding = EXCLUDED.embedding
                    """,
                    rows,
                )
            conn.commit()
            return len(chunks)
    except Exception as e:
        raise ValueError(
            f"Failed to index {len(chunks)} chunks for doc {doc_id}: {str(e)}"
        )
