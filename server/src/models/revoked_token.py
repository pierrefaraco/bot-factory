from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class RevokedToken(Base):
    """A logged-out access token, by jti. Kept until the token would have
    expired anyway (expires_at = its exp claim), then purged."""

    __tablename__ = "revoked_token"
    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def __init__(self, jti: str, expires_at: datetime):
        self.jti = jti
        self.expires_at = expires_at
