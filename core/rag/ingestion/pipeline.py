from dataclasses import dataclass
from typing import Optional
import psycopg
import logging

from core.models.clone_profile import CloneProfile
from core.rag.ingestion.parser import parse
from core.rag.ingestion.chunker import chunk_text
from core.rag.ingestion.embedder import get_embedder
from core.rag.ingestion.indexer import index_chunks

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    doc_id: str
    chunk_count: int
    status: str
    error_message: Optional[str] = None


class IngestionPipeline:

    def __init__(self, profile: CloneProfile, db_url: str):
        self.profile = profile
        self.db_url = db_url

    def ingest(
        self,
        file_path: str,
        doc_id: str,
        clone_id: str,
        source_type: str,
        provenance: dict,
    ) -> IngestResult:
        try:
            self._validate_provenance(provenance)

            self._update_status(doc_id, "processing")

            blocks = parse(file_path)
            logger.info(f"Parsed {len(blocks)} blocks from {file_path}")

            embedder = get_embedder()
            strategy = self.profile.chunking_strategy.value

            if strategy == "semantic":
                embedder._init_client()
                lc_embeddings = embedder._client
            else:
                lc_embeddings = None

            chunks = chunk_text(blocks, strategy=strategy, embeddings=lc_embeddings)
            logger.info(f"Chunked into {len(chunks)} chunks (strategy={strategy})")

            self._delete_existing_chunks(doc_id)

            embeddings = embedder.embed(chunks)
            logger.info(f"Generated {len(embeddings)} embeddings")

            access_tier = provenance.get("access_tier", "public")
            date = provenance.get("date")
            chunk_count = index_chunks(
                doc_id=doc_id,
                clone_id=clone_id,
                chunks=chunks,
                embeddings=embeddings,
                source_type=source_type,
                access_tier=access_tier,
                date=date,
                db_url=self.db_url,
            )

            self._update_status(doc_id, "complete", chunk_count)
            logger.info(f"✅ Ingested {doc_id}: {chunk_count} chunks")

            return IngestResult(
                doc_id=doc_id,
                chunk_count=chunk_count,
                status="complete",
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Ingestion failed for {doc_id}: {error_msg}")

            try:
                self._update_status(doc_id, "error")
            except Exception:
                pass

            return IngestResult(
                doc_id=doc_id,
                chunk_count=0,
                status="error",
                error_message=error_msg,
            )

    def _validate_provenance(self, provenance: dict) -> None:
        if self.profile.review_required:
            required = {"date", "location", "event", "verifier", "access_tier"}
            missing = required - set(provenance.keys())
            if missing:
                raise ValueError(
                    f"Sacred Archive requires provenance fields: {missing}"
                )
        else:
            if "access_tier" not in provenance:
                raise ValueError("Provenance must include 'access_tier'")

    def _delete_existing_chunks(self, doc_id: str) -> None:
        try:
            with psycopg.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM document_chunks WHERE doc_id = %s", (doc_id,)
                    )
                    deleted = cur.rowcount
                conn.commit()
                if deleted > 0:
                    logger.info(f"Deleted {deleted} old chunks for doc {doc_id}")
        except Exception as e:
            logger.warning(f"Failed to clean old chunks for {doc_id}: {e}")

    def _update_status(
        self,
        doc_id: str,
        status: str,
        chunk_count: Optional[int] = None,
    ) -> None:
        try:
            with psycopg.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    if chunk_count is not None:
                        cur.execute(
                            "UPDATE documents SET status = %s, chunk_count = %s WHERE id = %s",
                            (status, chunk_count, doc_id),
                        )
                    else:
                        cur.execute(
                            "UPDATE documents SET status = %s WHERE id = %s",
                            (status, doc_id),
                        )
                conn.commit()
        except Exception as e:
            raise ValueError(
                f"Failed to update documents table for {doc_id}: {str(e)}"
            )
