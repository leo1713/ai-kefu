from __future__ import annotations

from pydantic import BaseModel


class ApiKeySaveRequest(BaseModel):
    api_key: str


class SettingsResponse(BaseModel):
    anthropic_api_key: str | None = None
