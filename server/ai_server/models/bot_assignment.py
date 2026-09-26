from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ai_server.models.base import Base


class BotAssignment(Base):
    """Table de liaison pour assigner des bots spécifiques aux utilisateurs GUEST"""

    __tablename__ = "bot_guest_assignment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bot.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_account.id"), nullable=False
    )
    assigned_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_account.id"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        String(64),
        default=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"BotAssignment(id={self.id!r}, bot_id={self.bot_id!r}, user_id={self.user_id!r}, assigned_by={self.assigned_by!r}, assigned_at={self.assigned_at!r}, is_active={self.is_active!r})"

    def __init__(
        self, bot_id: int, user_id: int, assigned_by: int, is_active: bool = True
    ):
        self.bot_id = bot_id
        self.user_id = user_id
        self.assigned_by = assigned_by
        self.assigned_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S")
        self.is_active = is_active
