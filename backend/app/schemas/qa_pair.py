from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QAPairResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question: str
    answer: str
    keywords: list[str]
    category: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class QAPairCreate(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=4000)
    keywords: list[str] = Field(default_factory=list)
    category: str | None = Field(default=None, max_length=64)


class QAPairUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=1, max_length=500)
    answer: str | None = Field(default=None, min_length=1, max_length=4000)
    keywords: list[str] | None = None
    category: str | None = None
    is_active: bool | None = None
