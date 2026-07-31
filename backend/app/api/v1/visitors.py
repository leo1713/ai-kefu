from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.visitor import VisitorResponse, VisitorUpdateRequest
from app.services import visitor_service

router = APIRouter(prefix="/visitors", tags=["visitors"])


@router.get("", response_model=list[VisitorResponse])
async def list_visitors(
    search: str | None = Query(default=None, description="按 external_userid 或姓名模糊搜索"),
    tag: str | None = Query(default=None, description="按标签精确过滤"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[VisitorResponse]:
    visitors = await visitor_service.list_all(db, search=search, tag=tag, limit=limit)
    return [VisitorResponse.model_validate(v) for v in visitors]


@router.patch("/{visitor_id}", response_model=VisitorResponse)
async def update_visitor(
    visitor_id: uuid.UUID,
    body: VisitorUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> VisitorResponse:
    updates = body.model_dump(exclude_unset=True)
    visitor = await visitor_service.update_visitor(db, visitor_id, **updates)
    return VisitorResponse.model_validate(visitor)
