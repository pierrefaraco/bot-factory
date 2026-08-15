"""drop the iframe table (iframe embedding feature removed)

Revision ID: 9d21c47e5a03
Revises: 41a7c3440110
Create Date: 2026-08-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d21c47e5a03'
down_revision: Union[str, None] = '41a7c3440110'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('iframe')


def downgrade() -> None:
    op.create_table(
        'iframe',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bot_id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('allowed_origins', sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(['bot_id'], ['bot.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
