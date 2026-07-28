from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.chat import ChatRequest
from app.services.chat_service import chat_stream

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/completion")
async def post_chat_completion(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    return StreamingResponse(
        chat_stream(
            db,
            visitor_id=request.visitor_id,
            message=request.message,
            agent_id=request.agent_id,
            conversation_id=request.conversation_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
