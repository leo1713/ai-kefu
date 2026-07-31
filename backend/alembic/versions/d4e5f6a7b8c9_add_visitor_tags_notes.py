"""add visitor tags and notes

Revision ID: d4e5f6a7b8c9
Revises: c1a2b3d4e5f6
Create Date: 2026-07-31 02:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: str | None = 'c1a2b3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('visitors', sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('visitors', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('visitors', 'notes')
    op.drop_column('visitors', 'tags')
