from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowUpdate
from app.services import workflow_service

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    include_inactive: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> list[WorkflowResponse]:
    workflows = await workflow_service.list_workflows(db, include_inactive=include_inactive)
    return [WorkflowResponse.model_validate(wf) for wf in workflows]


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    body: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    wf = await workflow_service.create_workflow(
        db,
        name=body.name,
        description=body.description,
        trigger_keywords=body.trigger_keywords,
        definition=body.definition.model_dump(),
    )
    return WorkflowResponse.model_validate(wf)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    wf = await workflow_service.get_workflow(db, workflow_id)
    return WorkflowResponse.model_validate(wf)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    updates = body.model_dump(exclude_unset=True)
    if "definition" in updates and updates["definition"] is not None:
        updates["definition"] = json.dumps(updates["definition"], ensure_ascii=False)
    wf = await workflow_service.update_workflow(db, workflow_id, **updates)
    return WorkflowResponse.model_validate(wf)


@router.delete("/{workflow_id}", status_code=200)
async def delete_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await workflow_service.delete_workflow(db, workflow_id)
