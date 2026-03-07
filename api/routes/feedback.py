from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import get_clone, get_db
from core.models.clone_profile import CloneProfile
from core.db.schema import SeekerFeedback

router = APIRouter()


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)
    session_id: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    rating: int
    message: str


@router.post("/{clone_slug}")
async def submit_feedback(
    clone_slug: str,
    request: FeedbackRequest,
    clone_info: tuple[str, CloneProfile] = Depends(get_clone),
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    clone_id, profile = clone_info
    entry = SeekerFeedback(
        clone_id=clone_id,
        rating=request.rating,
        comment=request.comment,
        session_id=request.session_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return FeedbackResponse(id=str(entry.id), rating=entry.rating, message="Thank you for your feedback")
