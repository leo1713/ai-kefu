from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Visitor(Base):
    __tablename__ = "visitors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_userid: Mapped[str] = mapped_column(String(128), unique=True)
    name: Mapped[str | None] = mapped_column(String(128), default=None)
    avatar: Mapped[str | None] = mapped_column(String(512), default=None)
    ai_disabled: Mapped[bool] = mapped_column(default=False)
    tags: Mapped[list[Any]] = mapped_column(JSON, default=list, server_default="[]")
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)

    conversations: Mapped[list[Conversation]] = relationship(back_populates="visitor")

    __table_args__ = (Index("ix_visitors_external_userid", "external_userid"),)
