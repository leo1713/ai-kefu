from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    return await stats_service.get_overview(db)


@router.get("/daily")
async def daily(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    return await stats_service.get_daily_stats(db, days=days)
