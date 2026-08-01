from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.qa_pair import QAPairCreate, QAPairResponse, QAPairUpdate
from app.services import qa_service

router = APIRouter(prefix="/qa", tags=["qa"])


@router.get("", response_model=list[QAPairResponse])
async def list_qa(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[QAPairResponse]:
    pairs = await qa_service.list_qa(
        db, search=search, category=category,
        include_inactive=include_inactive, limit=limit,
    )
    return [QAPairResponse.model_validate(p) for p in pairs]


@router.post("", response_model=QAPairResponse, status_code=201)
async def create_qa(
    body: QAPairCreate,
    db: AsyncSession = Depends(get_db),
) -> QAPairResponse:
    pair = await qa_service.create_qa(
        db, question=body.question, answer=body.answer,
        keywords=body.keywords, category=body.category,
    )
    return QAPairResponse.model_validate(pair)


@router.put("/{qa_id}", response_model=QAPairResponse)
async def update_qa(
    qa_id: uuid.UUID,
    body: QAPairUpdate,
    db: AsyncSession = Depends(get_db),
) -> QAPairResponse:
    updates = body.model_dump(exclude_unset=True)
    pair = await qa_service.update_qa(db, qa_id, **updates)
    return QAPairResponse.model_validate(pair)


@router.delete("/{qa_id}", status_code=200)
async def delete_qa(
    qa_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await qa_service.delete_qa(db, qa_id)


class BatchImportRequest(BaseModel):
    items: list[QAPairCreate]


class BatchImportResponse(BaseModel):
    imported: int


@router.post("/batch", response_model=BatchImportResponse)
async def batch_import(
    body: BatchImportRequest,
    db: AsyncSession = Depends(get_db),
) -> BatchImportResponse:
    items = [i.model_dump() for i in body.items]
    count = await qa_service.batch_import(db, items)
    return BatchImportResponse(imported=count)
