from datetime import datetime, timezone
from typing import Optional

import sqlalchemy
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class MagicLink(Base):
    """One-time login link (https://<app>/auth?token=<token>).

    Only the SHA-256 of the token is stored: a DB dump or a read-only SQL
    injection must not hand out working login links. used_at is set when
    the link is redeemed; a link is valid while used_at is NULL and
    expires_at is in the future (see MagicLinkRepository.consume)."""

    __tablename__ = "magic_link"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        server_default=sqlalchemy.text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        # token_hash left out on purpose: it has no business in logs.
        return (
            f"MagicLink(id={self.id!r}, user_id={self.user_id!r}, "
            f"expires_at={self.expires_at!r}, used_at={self.used_at!r})"
        )

    def __init__(self, user_id: int, token_hash: str, expires_at: datetime):
        self.user_id = user_id
        self.token_hash = token_hash
        self.expires_at = expires_at
