from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ai_server.models.base import Base


class TokenUsage(Base):
    __tablename__ = "token_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), nullable=False)
    user_guest_id: Mapped[int] = mapped_column(nullable=True)
    bot_id: Mapped[int] = mapped_column(nullable=False)
    session_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    def __repr__(self) -> str:
        return (
            f"TokenUsage(id={self.id!r}, user_id={self.user_id!r}, user_guest_id={self.user_guest_id!r}, bot_id={self.bot_id!r}, "
            f"session_id={self.session_id!r}, prompt_tokens={self.prompt_tokens!r}, "
            f"completion_tokens={self.completion_tokens!r}, total_tokens={self.total_tokens!r}, "
            f"timestamp={self.timestamp!r}, model_name={self.model_name!r})"
        )

    def __init__(
        self,
        user_id: int,
        user_guest_id: int,
        bot_id: int,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        session_id: Optional[int] = None,
        model_name: Optional[str] = None,
    ):
        self.user_id = user_id
        self.user_guest_id = user_guest_id
        self.bot_id = bot_id
        self.session_id = session_id
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.model_name = model_name
