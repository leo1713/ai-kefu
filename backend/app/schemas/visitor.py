from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VisitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_userid: str
    name: str | None
    avatar: str | None
    ai_disabled: bool
    tags: list[str]
    notes: str | None
    created_at: datetime
    updated_at: datetime


class VisitorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    tags: list[str] | None = None
    notes: str | None = Field(default=None, max_length=2000)
    ai_disabled: bool | None = None
