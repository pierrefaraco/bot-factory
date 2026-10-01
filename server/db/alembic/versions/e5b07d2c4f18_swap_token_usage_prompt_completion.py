"""swap token_usage.prompt_tokens / completion_tokens on existing rows

TokenCountingCallback stored LangChain's output_tokens as prompt_tokens
and input_tokens as completion_tokens. Every row written before this
revision comes from that code (migrations run before the API serves), so
all of them are swapped back. total_tokens was right and is untouched.

Revision ID: e5b07d2c4f18
Revises: d81f5c3a9e60
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5b07d2c4f18'
down_revision: Union[str, None] = 'd81f5c3a9e60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# MySQL evaluates single-table UPDATE assignments left to right, each one
# seeing the previous ones' results: a plain "a = b, b = a" would copy b
# into both. Swapping through the sum avoids a temporary column.
SWAP = """
    UPDATE token_usage
    SET prompt_tokens = prompt_tokens + completion_tokens,
        completion_tokens = prompt_tokens - completion_tokens,
        prompt_tokens = prompt_tokens - completion_tokens
"""


def upgrade() -> None:
    op.execute(SWAP)


def downgrade() -> None:
    op.execute(SWAP)
