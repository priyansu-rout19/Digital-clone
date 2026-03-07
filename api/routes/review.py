from typing import Optional, Literal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from api.deps import get_clone, get_db
from api.auth import require_role
from core.models.clone_profile import CloneProfile
from core.db.schema import ReviewQueue, AuditDetails
from core.audit import write_audit, extract_actor


router = APIRouter()


class ReviewItem(BaseModel):
    id: str
    query_text: str
    response_text: str
    confidence_score: Optional[float]
    cited_sources: Optional[list] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewUpdateRequest(BaseModel):
    action: Literal["approve", "reject", "edit"]
    notes: Optional[str] = None
    edited_response: Optional[str] = None


class ReviewUpdateResponse(BaseModel):
    id: str
    status: str
    response_text: Optional[str] = None
    reviewer_notes: Optional[str]
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReviewStatusResponse(BaseModel):
    id: str
    status: str
    response_text: Optional[str] = None
    reviewed_at: Optional[datetime] = None


@router.get("/{clone_slug}")
async def list_pending_reviews(
    clone_slug: str,
    clone_info: tuple[str, CloneProfile] = Depends(get_clone),
    db: Session = Depends(get_db),
) -> list[ReviewItem]:
    """
    List pending reviews for a clone (Sacred Archive only).
    Returns all responses in the review queue with status="pending".
    """
    clone_id, profile = clone_info

    # Check if this clone requires review
    if not profile.review_required:
        raise HTTPException(
            status_code=403,
            detail=f"Clone '{clone_slug}' does not have review_required=true",
        )

    # Query pending reviews
    pending = (
        db.query(ReviewQueue)
        .filter(and_(ReviewQueue.clone_id == clone_id, ReviewQueue.status.in_(["pending", "edited"])))
        .order_by(ReviewQueue.created_at.desc())
        .all()
    )

    return [
        ReviewItem(
            id=str(item.id),
            query_text=item.query_text,
            response_text=item.response_text,
            confidence_score=item.confidence_score,
            cited_sources=item.cited_sources,
            created_at=item.created_at,
        )
        for item in pending
    ]


@router.patch("/{clone_slug}/{review_id}")
async def update_review(
    clone_slug: str,
    review_id: str,
    request: ReviewUpdateRequest,
    http_request: Request,
    actor_role: str = Depends(require_role("reviewer", "curator")),
    clone_info: tuple[str, CloneProfile] = Depends(get_clone),
    db: Session = Depends(get_db),
) -> ReviewUpdateResponse:
    """
    Approve or reject a review (clone-scoped for multi-tenant isolation).
    Updates the review_queue table with the decision and timestamp.
    """
    clone_id, profile = clone_info

    # Load the review and verify it belongs to this clone
    review = db.query(ReviewQueue).filter(
        and_(ReviewQueue.id == review_id, ReviewQueue.clone_id == clone_id)
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found for clone '{clone_slug}'")

    previous_status = review.status

    # Handle edit action
    if request.action == "edit":
        if not request.edited_response or not request.edited_response.strip():
            raise HTTPException(status_code=400, detail="edited_response is required for edit action")
        review.response_text = request.edited_response.strip()
        review.status = "edited"
        review.reviewer_notes = request.notes
        review.reviewed_at = datetime.utcnow()
    else:
        # Update status and reviewer notes
        new_status = "approved" if request.action == "approve" else "rejected"
        review.status = new_status
        review.reviewer_notes = request.notes
        review.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(review)

    # Audit trail
    actor_id, _ = extract_actor(http_request)
    write_audit(
        db,
        clone_id=clone_id,
        action=f"review.{request.action}",
        actor_id=actor_id,
        actor_role=actor_role,
        details=AuditDetails(
            response_id=review_id,
            decision=request.action,
            reason=request.notes,
            confidence_score=review.confidence_score,
            previous_status=previous_status,
            new_status=review.status,
        ),
    )

    return ReviewUpdateResponse(
        id=str(review.id),
        status=review.status,
        response_text=review.response_text,
        reviewer_notes=review.reviewer_notes,
        reviewed_at=review.reviewed_at,
    )


@router.get("/{clone_slug}/status/{review_id}")
async def get_review_status(
    clone_slug: str,
    review_id: str,
    clone_info: tuple[str, CloneProfile] = Depends(get_clone),
    db: Session = Depends(get_db),
) -> ReviewStatusResponse:
    """
    Check the review status of a specific response.
    Used by the seeker's frontend to poll for reviewer decisions.
    Clone-scoped for multi-tenant isolation.

    Only returns response_text for approved/edited — rejected text is not leaked.
    """
    clone_id, profile = clone_info

    review = db.query(ReviewQueue).filter(
        and_(ReviewQueue.id == review_id, ReviewQueue.clone_id == clone_id)
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return ReviewStatusResponse(
        id=str(review.id),
        status=review.status,
        response_text=review.response_text if review.status in ("approved", "edited") else None,
        reviewed_at=review.reviewed_at,
    )
