"""
Analytics API — monitoring dashboard data.

Reads from query_analytics table (populated by chat handlers after each query).
Provides aggregate stats: total queries, avg confidence, avg latency, silence rate,
queries per day, and top intent classes.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from api.deps import get_clone, get_db
from core.db.schema import QueryAnalytics
from core.models.clone_profile import CloneProfile

router = APIRouter()
logger = logging.getLogger(__name__)


class AnalyticsSummary(BaseModel):
    total_queries: int
    avg_confidence: Optional[float]
    avg_latency_ms: Optional[float]
    silence_rate: float  # 0.0-1.0
    queries_per_day: list[dict]  # [{date: str, count: int}]
    top_intents: list[dict]  # [{intent: str, count: int}]


@router.get("/{clone_slug}")
async def get_analytics(
    clone_slug: str,
    clone_info: tuple[str, CloneProfile] = Depends(get_clone),
    db: Session = Depends(get_db),
) -> AnalyticsSummary:
    """
    Get aggregate analytics for a clone.

    Returns total queries, average confidence, average latency,
    silence rate, queries per day (last 30 days), and top intent classes.
    """
    clone_id, _ = clone_info

    # Total queries
    total = db.query(func.count(QueryAnalytics.id)).filter(
        QueryAnalytics.clone_id == clone_id
    ).scalar() or 0

    if total == 0:
        return AnalyticsSummary(
            total_queries=0,
            avg_confidence=None,
            avg_latency_ms=None,
            silence_rate=0.0,
            queries_per_day=[],
            top_intents=[],
        )

    # Avg confidence
    avg_conf = db.query(func.avg(QueryAnalytics.confidence_score)).filter(
        QueryAnalytics.clone_id == clone_id
    ).scalar()

    # Avg latency
    avg_lat = db.query(func.avg(QueryAnalytics.latency_ms)).filter(
        QueryAnalytics.clone_id == clone_id
    ).scalar()

    # Silence rate
    silence_count = db.query(func.count(QueryAnalytics.id)).filter(
        QueryAnalytics.clone_id == clone_id,
        QueryAnalytics.silence_triggered == True,
    ).scalar() or 0
    silence_rate = silence_count / total if total > 0 else 0.0

    # Queries per day (last 30 days)
    daily_rows = (
        db.query(
            cast(QueryAnalytics.created_at, Date).label("date"),
            func.count(QueryAnalytics.id).label("count"),
        )
        .filter(QueryAnalytics.clone_id == clone_id)
        .group_by(cast(QueryAnalytics.created_at, Date))
        .order_by(cast(QueryAnalytics.created_at, Date).desc())
        .limit(30)
        .all()
    )
    queries_per_day = [{"date": str(row.date), "count": row.count} for row in daily_rows]

    # Top intent classes
    intent_rows = (
        db.query(
            QueryAnalytics.intent_class,
            func.count(QueryAnalytics.id).label("count"),
        )
        .filter(
            QueryAnalytics.clone_id == clone_id,
            QueryAnalytics.intent_class.isnot(None),
            QueryAnalytics.intent_class != "",
        )
        .group_by(QueryAnalytics.intent_class)
        .order_by(func.count(QueryAnalytics.id).desc())
        .limit(5)
        .all()
    )
    top_intents = [{"intent": row.intent_class, "count": row.count} for row in intent_rows]

    return AnalyticsSummary(
        total_queries=total,
        avg_confidence=round(avg_conf, 3) if avg_conf is not None else None,
        avg_latency_ms=round(avg_lat, 1) if avg_lat is not None else None,
        silence_rate=round(silence_rate, 3),
        queries_per_day=queries_per_day,
        top_intents=top_intents,
    )
