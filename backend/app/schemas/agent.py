import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    name: str
    system_prompt: str = ""
    model: str = "claude-sonnet-4-20250514"
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2000, ge=1, le=8096)
    is_default: bool = False


class AgentUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1, le=8096)
    slug: str | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    system_prompt: str
    model: str
    temperature: float
    max_tokens: int
    is_default: bool
    slug: str | None
    created_at: datetime
    updated_at: datetime
