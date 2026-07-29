import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    return await conversation_service.list_all(db)


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    msgs = await conversation_service.get_messages(db, conversation_id)
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "msg_type": m.msg_type,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]
