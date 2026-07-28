import uuid

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    name: str
    system_prompt: str = ""
    model: str = "claude-sonnet-4-20250514"
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2000, ge=1, le=8096)
    tools: list[str] = Field(default_factory=list)
    knowledge_ids: list[uuid.UUID] = Field(default_factory=list)
    workflow_id: uuid.UUID | None = None


class ChatMessage(BaseModel):
    role: str
    content: str
