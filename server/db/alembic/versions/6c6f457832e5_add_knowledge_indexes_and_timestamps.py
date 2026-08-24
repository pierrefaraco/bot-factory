"""add knowledge indexes, created_at/updated_at, vector_synced_at

Revision ID: 6c6f457832e5
Revises: 55e7c5ed01c7
Create Date: 2026-08-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c6f457832e5'
down_revision: Union[str, None] = '55e7c5ed01c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'knowledge',
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
    )
    op.add_column(
        'knowledge',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
    )
    op.add_column(
        'knowledge',
        sa.Column('vector_synced_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_knowledge_bot_id', 'knowledge', ['bot_id'])
    op.create_index('ix_knowledge_knowledge_dad_id', 'knowledge', ['knowledge_dad_id'])


def downgrade() -> None:
    op.drop_index('ix_knowledge_knowledge_dad_id', table_name='knowledge')
    op.drop_index('ix_knowledge_bot_id', table_name='knowledge')
    op.drop_column('knowledge', 'vector_synced_at')
    op.drop_column('knowledge', 'updated_at')
    op.drop_column('knowledge', 'created_at')
