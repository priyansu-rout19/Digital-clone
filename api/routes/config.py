from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_clone, get_db
from core.models.clone_profile import CloneProfile


router = APIRouter()


@router.get("/{clone_slug}/profile")
async def get_clone_profile(
    clone_slug: str,
    clone_id_and_profile: tuple[str, CloneProfile] = Depends(get_clone),
) -> dict:
    """
    Get the CloneProfile configuration for a clone.
    Returns the full profile as JSON.
    """
    clone_id, profile = clone_id_and_profile
    return profile.model_dump()
