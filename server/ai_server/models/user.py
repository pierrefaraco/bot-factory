from datetime import datetime, timezone
from typing import Optional

import sqlalchemy
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ai_server.models.base import Base


class User(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(256))
    mail: Mapped[str] = mapped_column(String(128))
    roles: Mapped[str] = mapped_column(String(128))
    parent_id: Mapped[int] = mapped_column()
    is_active: Mapped[bool] = mapped_column()
    # use_alter=True: 'bot' and 'user_account' reference each other
    # (bot.user_account_id <-> user_account.selected_bot_id). Without this,
    # SQLAlchemy/Alembic can't order CREATE TABLE statements (circular FK)
    # and autogenerate emits an unresolved-cycle warning. use_alter tells
    # SQLAlchemy to create/drop this specific constraint via a separate
    # ALTER TABLE, after both tables already exist.
    selected_bot_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(
            "bot.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_user_account_selected_bot_id",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        server_default=sqlalchemy.text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, password_hash={self.password_hash!r}, mail={self.mail!r}), roles={self.roles!r}, parent_id={self.parent_id!r}, is_active={self.is_active!r}, selected_bot_id={self.selected_bot_id!r}, created_at={self.created_at!r})"

    def __init__(
        self,
        name: str,
        password_hash: str,
        mail: str,
        roles: str,
        parent_id: int,
        is_active: bool,
        selected_bot_id: Optional[int] = None,
    ):
        self.name = name
        self.password_hash = password_hash
        self.mail = mail
        self.roles = roles
        self.parent_id = parent_id
        self.is_active = is_active
        self.selected_bot_id = selected_bot_id
