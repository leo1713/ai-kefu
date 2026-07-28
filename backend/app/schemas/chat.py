import uuid

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    visitor_id: str
    conversation_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None


class SSEEvent(BaseModel):
    event: str
    data: dict[str, object]
