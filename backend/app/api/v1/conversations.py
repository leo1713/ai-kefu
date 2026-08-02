import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.staff import Staff
from app.schemas.conversation import (
    AssignStaffRequest,
    ConversationResponse,
    ReplyRequest,
    TransferRequest,
)
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    status: str | None = Query(
        default=None, description="按状态过滤: active | transferred | closed"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> list[dict[str, object]]:
    return await conversation_service.list_all(db, limit=limit, status=status)


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
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


@router.post("/{conversation_id}/transfer", response_model=ConversationResponse)
async def transfer_conversation(
    conversation_id: uuid.UUID,
    body: TransferRequest,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> ConversationResponse:
    conv = await conversation_service.transfer_conversation(
        db, conversation_id=conversation_id, reason=body.reason
    )
    return ConversationResponse.model_validate(conv)


@router.post("/{conversation_id}/assign", response_model=ConversationResponse)
async def assign_staff_to_conversation(
    conversation_id: uuid.UUID,
    body: AssignStaffRequest,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> ConversationResponse:
    conv = await conversation_service.assign_staff(
        db, conversation_id=conversation_id, staff_id=body.staff_id
    )
    return ConversationResponse.model_validate(conv)


@router.patch("/{conversation_id}/close", response_model=ConversationResponse)
async def close_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> ConversationResponse:
    conv = await conversation_service.close_conversation(db, conversation_id)
    return ConversationResponse.model_validate(conv)


@router.post("/{conversation_id}/reply")
async def reply_to_conversation(
    conversation_id: uuid.UUID,
    body: ReplyRequest,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_user),
) -> dict[str, object]:
    msg = await conversation_service.reply_and_send_wecom(
        db, conversation_id=conversation_id, content=body.content
    )
    return {
        "id": str(msg.id),
        "role": msg.role,
        "content": msg.content,
        "msg_type": msg.msg_type,
        "created_at": msg.created_at.isoformat(),
    }
