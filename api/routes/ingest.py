import os
import json
import uuid
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import insert, and_
from datetime import datetime

from api.deps import get_clone, get_db
from core.models.clone_profile import CloneProfile
from core.db.schema import Document, AuditDetails
from core.rag.ingestion.pipeline import IngestionPipeline
from core.audit import write_audit, extract_actor


from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


class IngestResponse(BaseModel):
    job_id: str
    status: str
    message: str


class IngestStatusResponse(BaseModel):
    doc_id: str
    filename: str
    status: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    message: str


def run_ingest_task(
    clone_id: str,
    doc_id: str,
    file_path: str,
    source_type: str,
    provenance: dict,
    profile: CloneProfile,
    db_url: str,
):
    """
    Background task: Run the ingestion pipeline.
    Called via BackgroundTasks (fire-and-forget).
    """
    try:
        pipeline = IngestionPipeline(profile=profile, db_url=db_url)
        result = pipeline.ingest(
            file_path=file_path,
            doc_id=doc_id,
            clone_id=clone_id,
            source_type=source_type,
            provenance=provenance,
        )
        print(f"Ingest complete for {doc_id}: {result.status}")
    except Exception as e:
        print(f"Ingest failed for {doc_id}: {str(e)}")


@router.post("/{clone_slug}")
@limiter.limit("10/minute")
async def ingest_file(
    request: Request,
    clone_slug: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_type: str = Form("document"),
    provenance_json: Optional[str] = Form(None),
    clone_info: tuple[str, CloneProfile] = Depends(get_clone),
    db: Session = Depends(get_db),
) -> IngestResponse:
    """
    Upload a document and trigger background ingestion.

    Form fields:
    - file: UploadFile (PDF, markdown, text)
    - source_type: str (e.g., "book", "lecture", "pdf")
    - provenance_json: Optional[str] (JSON dict with date, location, event, verifier, access_tier)

    Returns immediately with job_id. Ingestion happens in background.
    """
    clone_id, profile = clone_info

    # Parse provenance
    provenance = {}
    if provenance_json:
        try:
            provenance = json.loads(provenance_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid provenance_json")

    # Validate provenance for Sacred Archive
    if profile.review_required:
        required_fields = {"date", "location", "event", "verifier", "access_tier"}
        missing = required_fields - set(provenance.keys())
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Sacred Archive requires provenance fields: {missing}",
            )

    # Generate doc_id and create upload directory
    doc_id = str(uuid.uuid4())
    upload_dir = Path(f"/tmp/dce_uploads/{doc_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    file_path = upload_dir / Path(file.filename).name
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Insert document row into DB (required before calling IngestionPipeline.ingest())
    db.execute(
        insert(Document).values(
            id=doc_id,
            clone_id=clone_id,
            filename=file.filename,
            mime_type=file.content_type,
            file_path=str(file_path),
            source_type=source_type,
            provenance=provenance,
            status="queued",
        )
    )
    db.commit()

    # Audit trail
    actor_id, actor_role = extract_actor(request)
    write_audit(
        db,
        clone_id=clone_id,
        action="ingest.upload",
        actor_id=actor_id,
        actor_role=actor_role or "admin",
        details=AuditDetails(
            query_id=doc_id,
            reason=f"filename={Path(file.filename).name}, source_type={source_type}",
        ),
    )

    # Trigger background ingestion task
    db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://localhost/dce_dev").replace("+psycopg", "")
    background_tasks.add_task(
        run_ingest_task,
        clone_id=clone_id,
        doc_id=doc_id,
        file_path=str(file_path),
        source_type=source_type,
        provenance=provenance,
        profile=profile,
        db_url=db_url,
    )

    return IngestResponse(
        job_id=doc_id,
        status="processing",
        message=f"File {file.filename} queued for ingestion",
    )


@router.get("/{clone_slug}/status/{doc_id}")
async def get_ingest_status(
    clone_slug: str,
    doc_id: str,
    clone_info: tuple[str, CloneProfile] = Depends(get_clone),
    db: Session = Depends(get_db),
) -> IngestStatusResponse:
    """
    Poll the ingestion status for a specific document.

    Uses clone_id + doc_id together for cross-clone isolation:
    a client cannot query another clone's documents.

    Status values:
    - queued: Document is queued for ingestion
    - processing: Ingestion in progress
    - complete: Ingestion finished successfully
    - error: Ingestion failed
    """
    clone_id, profile = clone_info

    # Query with both doc_id and clone_id for cross-clone isolation
    doc = (
        db.query(Document)
        .filter(and_(Document.id == doc_id, Document.clone_id == clone_id))
        .first()
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{doc_id}' not found for clone '{clone_slug}'",
        )

    # Map status to human-readable message
    message_map = {
        "complete": f"Ingestion complete — {doc.chunk_count} chunks indexed",
        "processing": "Ingestion in progress",
        "queued": "Document is queued for ingestion",
    }
    message = message_map.get(doc.status, "Ingestion failed — please re-upload the document")

    return IngestStatusResponse(
        doc_id=str(doc.id),
        filename=doc.filename,
        status=doc.status,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        message=message,
    )
