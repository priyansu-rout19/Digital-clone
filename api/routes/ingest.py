import os
import json
import uuid
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import insert

from api.deps import get_clone, get_db
from core.models.clone_profile import CloneProfile
from core.db.schema import Document
from core.rag.ingestion.pipeline import IngestionPipeline


router = APIRouter()


class IngestResponse(BaseModel):
    job_id: str
    status: str
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
async def ingest_file(
    clone_slug: str,
    file: UploadFile = File(...),
    source_type: str = Form("document"),
    provenance_json: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
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
    file_path = upload_dir / file.filename
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Insert document row into DB (required before calling IngestionPipeline.ingest())
    db.execute(
        insert(Document).values(
            id=doc_id,
            clone_id=clone_id,
            title=file.filename,
            author="",  # Not provided in request
            source_date=provenance.get("date"),
            source_location=provenance.get("location"),
            source_type=source_type,
            upload_id=doc_id,
            status="pending",
            metadata_={},
        )
    )
    db.commit()

    # Trigger background ingestion task
    db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://localhost/dce_dev")
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
