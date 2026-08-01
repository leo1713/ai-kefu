"""add agent slug

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-08-01 08:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = 'f7a8b9c0d1e2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('agents', sa.Column('slug', sa.String(64), nullable=True))
    op.create_unique_constraint('uk_agents_slug', 'agents', ['slug'])


def downgrade() -> None:
    op.drop_constraint('uk_agents_slug', 'agents', type_='unique')
    op.drop_column('agents', 'slug')
