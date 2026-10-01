"""add revoked_token table (logout survives restarts and workers)

Revision ID: d81f5c3a9e60
Revises: c4a9e2f17b3d
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd81f5c3a9e60'
down_revision: Union[str, None] = 'c4a9e2f17b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'revoked_token',
        sa.Column('jti', sa.String(length=36), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('jti'),
    )
    op.create_index(
        op.f('ix_revoked_token_expires_at'), 'revoked_token', ['expires_at'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_revoked_token_expires_at'), table_name='revoked_token')
    op.drop_table('revoked_token')
