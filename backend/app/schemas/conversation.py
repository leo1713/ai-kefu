import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    visitor_id: uuid.UUID
    status: str
    assigned_staff_id: uuid.UUID | None
    transfer_reason: str | None
    created_at: datetime
    updated_at: datetime


class TransferRequest(BaseModel):
    reason: str = "管理员手动转人工"


class AssignStaffRequest(BaseModel):
    staff_id: uuid.UUID


class ReplyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
