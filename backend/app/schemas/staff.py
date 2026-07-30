import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StaffCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6)
    display_name: str = Field(min_length=1, max_length=128)
    wecom_userid: str | None = None


class StaffUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    wecom_userid: str | None = None
    is_active: bool | None = None


class StaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    wecom_userid: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
