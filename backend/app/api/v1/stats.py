from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.staff import Staff
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> dict[str, object]:
    return await stats_service.get_overview(db)


@router.get("/daily")
async def daily(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> list[dict[str, object]]:
    return await stats_service.get_daily_stats(db, days=days)
