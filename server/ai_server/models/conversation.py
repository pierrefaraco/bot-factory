from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ai_server.models.base import Base


class Session(Base):
    __tablename__ = "session"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))

    def __repr__(self) -> str:
        return (
            f"Session(id={self.id!r}, bot_id={self.bot_id!r}, user_id={self.user_id!r})"
        )

    def __init__(self, bot_id: int, user_id: int):
        self.bot_id = bot_id
        self.user_id = user_id


# Define the Message model
class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("session.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(String(4096), nullable=False)
    time: Mapped[datetime] = mapped_column(
        String(64), default=datetime.now(timezone.utc), nullable=False
    )
    hide: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self) -> str:
        return f"Message(id={self.id!r},order={self.order!r},session_id={self.session_id!r}, role={self.role!r}, content={self.content!r}, time={self.time!r}),hide={self.hide!r})"

    def __init__(
        self,
        order,
        session_id: int,
        role: str,
        content: str,
        time: Optional[datetime] = None,
        hide: bool = False,
    ):
        self.order = order
        self.session_id = session_id
        self.role = role
        self.content = content
        self.time = time
        self.hide = hide
