"""add knowledge.pdf_path (per-bot, uuid-named PDF storage)

Revision ID: c4a9e2f17b3d
Revises: b3f1e8a27c90
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4a9e2f17b3d'
down_revision: Union[str, None] = 'b3f1e8a27c90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing rows keep pdf_path NULL: their file stays where it was,
    # directly under UPLOAD_FOLDER (see KnowledgeSvc._pdf_full_path).
    op.add_column('knowledge', sa.Column('pdf_path', sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column('knowledge', 'pdf_path')
