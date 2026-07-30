from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.staff import Staff
    from app.models.visitor import Visitor


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visitor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visitors.id"))
    # status: active | transferred | closed
    status: Mapped[str] = mapped_column(String(32), default="active")
    # 转人工后分配的客服
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff.id"), default=None
    )
    # 转人工原因（由 AI 填写）
    transfer_reason: Mapped[str | None] = mapped_column(String(512), default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)

    visitor: Mapped[Visitor] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", order_by="Message.created_at"
    )
    assigned_staff: Mapped[Staff | None] = relationship(
        back_populates="assigned_conversations"
    )

    __table_args__ = (
        Index("ix_conversations_visitor_id", "visitor_id"),
        Index("ix_conversations_assigned_staff_id", "assigned_staff_id"),
    )
