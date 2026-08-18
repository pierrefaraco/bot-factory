"""add user_account.created_at

Revision ID: 55e7c5ed01c7
Revises: 9d21c47e5a03
Create Date: 2026-08-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55e7c5ed01c7'
down_revision: Union[str, None] = '9d21c47e5a03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'user_account',
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
    )


def downgrade() -> None:
    op.drop_column('user_account', 'created_at')
