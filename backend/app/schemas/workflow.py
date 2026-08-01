from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class WorkflowNode(BaseModel):
    id: str
    type: Literal["send_message", "condition", "tool_call", "end", "llm"]
    data: dict[str, Any] = {}
    next: str | None = None
    next_true: str | None = None
    next_false: str | None = None


class WorkflowDefinition(BaseModel):
    nodes: list[WorkflowNode]
    start: str


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    trigger_keywords: list[str] = []
    definition: WorkflowDefinition


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger_keywords: list[str] | None = None
    definition: WorkflowDefinition | None = None
    is_active: bool | None = None


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    trigger_keywords: list[str]
    definition: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
