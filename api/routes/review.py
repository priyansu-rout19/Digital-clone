from typing import Optional, Literal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from api.deps import get_clone, get_db
from core.models.clone_profile import CloneProfile
from core.db.schema import ReviewQueue


router = APIRouter()


class ReviewItem(BaseModel):
    id: str
    query_text: str
    response_text: str
    confidence_score: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewUpdateRequest(BaseModel):
    action: Literal["approve", "reject"]
    notes: Optional[str] = None


class ReviewUpdateResponse(BaseModel):
    id: str
    status: str
    reviewer_notes: Optional[str]
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True


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
        .filter(and_(ReviewQueue.clone_id == clone_id, ReviewQueue.status == "pending"))
        .order_by(ReviewQueue.created_at.desc())
        .all()
    )

    return [
        ReviewItem(
            id=str(item.id),
            query_text=item.query_text,
            response_text=item.response_text,
            confidence_score=item.confidence_score,
            created_at=item.created_at,
        )
        for item in pending
    ]


@router.patch("/{review_id}")
async def update_review(
    review_id: str,
    request: ReviewUpdateRequest,
    db: Session = Depends(get_db),
) -> ReviewUpdateResponse:
    """
    Approve or reject a review.
    Updates the review_queue table with the decision and timestamp.
    """
    # Load the review
    review = db.query(ReviewQueue).filter(ReviewQueue.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found")

    # Update status and reviewer notes
    new_status = "approved" if request.action == "approve" else "rejected"
    review.status = new_status
    review.reviewer_notes = request.notes
    review.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(review)

    return ReviewUpdateResponse(
        id=str(review.id),
        status=review.status,
        reviewer_notes=review.reviewer_notes,
        reviewed_at=review.reviewed_at,
    )
