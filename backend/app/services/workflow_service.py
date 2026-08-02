from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow

logger = structlog.get_logger()


async def list_workflows(
    db: AsyncSession,
    include_inactive: bool = False,
) -> list[Workflow]:
    stmt = (
        select(Workflow)
        .where(Workflow.deleted_at.is_(None))
        .order_by(Workflow.updated_at.desc())
    )
    if not include_inactive:
        stmt = stmt.where(Workflow.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_workflow(db: AsyncSession, workflow_id: uuid.UUID) -> Workflow:
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.deleted_at.is_(None))
    )
    wf = result.scalar_one_or_none()
    if not wf:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Workflow {workflow_id} not found")
    return wf


async def create_workflow(
    db: AsyncSession,
    name: str,
    definition: dict[str, object],
    description: str | None = None,
    trigger_keywords: list[str] | None = None,
) -> Workflow:
    wf = Workflow(
        name=name,
        description=description,
        trigger_keywords=trigger_keywords or [],
        definition=json.dumps(definition, ensure_ascii=False),
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    logger.info("workflow_created", workflow_id=str(wf.id), name=name)
    return wf


async def update_workflow(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    **kwargs: object,
) -> Workflow:
    wf = await get_workflow(db, workflow_id)
    if "definition" in kwargs and isinstance(kwargs["definition"], dict):
        kwargs["definition"] = json.dumps(kwargs["definition"], ensure_ascii=False)
    for k, v in kwargs.items():
        setattr(wf, k, v)
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf


async def delete_workflow(db: AsyncSession, workflow_id: uuid.UUID) -> None:
    wf = await get_workflow(db, workflow_id)
    wf.deleted_at = datetime.now(UTC)
    db.add(wf)
    await db.commit()


async def match_workflow(db: AsyncSession, message: str) -> Workflow | None:
    """Return first active workflow whose trigger_keywords appear in message."""
    result = await db.execute(
        select(Workflow).where(
            Workflow.is_active.is_(True),
            Workflow.deleted_at.is_(None),
        )
    )
    workflows = list(result.scalars().all())
    msg_lower = message.lower()
    for wf in workflows:
        keywords: list[str] = wf.trigger_keywords or []
        if any(kw.lower() in msg_lower for kw in keywords if kw):
            logger.info("workflow_triggered", workflow_id=str(wf.id), name=wf.name)
            return wf
    return None
