"""add knowledge chunks with pgvector

Revision ID: b35b2a9eed22
Revises: a3e7b60320c6
Create Date: 2026-07-28 08:49:12.891223

"""
from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b35b2a9eed22'
down_revision: str | None = 'a3e7b60320c6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table('knowledge_chunks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('collection_id', sa.Uuid(), nullable=False),
    sa.Column('document_name', sa.String(length=256), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['collection_id'], ['knowledge_collections.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_chunks_collection_id', 'knowledge_chunks', ['collection_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_knowledge_chunks_collection_id', table_name='knowledge_chunks')
    op.drop_table('knowledge_chunks')
    # ### end Alembic commands ###
