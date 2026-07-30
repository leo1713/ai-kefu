"""add handoff fields to conversations and staff

Revision ID: c1a2b3d4e5f6
Revises: e5ff7b8b64db
Create Date: 2026-07-30 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1a2b3d4e5f6"
down_revision: str | None = "e5ff7b8b64db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Staff: 新增 wecom_userid 字段
    op.add_column(
        "staff",
        sa.Column("wecom_userid", sa.String(length=128), nullable=True),
    )

    # Conversations: 新增 assigned_staff_id FK 和 transfer_reason
    op.add_column(
        "conversations",
        sa.Column("assigned_staff_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("transfer_reason", sa.String(length=512), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversations_assigned_staff_id",
        "conversations",
        "staff",
        ["assigned_staff_id"],
        ["id"],
    )
    op.create_index(
        "ix_conversations_assigned_staff_id",
        "conversations",
        ["assigned_staff_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_assigned_staff_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_assigned_staff_id", "conversations", type_="foreignkey"
    )
    op.drop_column("conversations", "transfer_reason")
    op.drop_column("conversations", "assigned_staff_id")
    op.drop_column("staff", "wecom_userid")
