import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    """手动触发转人工请求体。"""
    reason: str = "管理员手动转人工"


class AssignStaffRequest(BaseModel):
    """手动分配客服请求体。"""
    staff_id: uuid.UUID


