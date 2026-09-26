from datetime import datetime
from typing import Optional

import sqlalchemy
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ai_server.models.base import Base

ROOT_CHAPTER_ID = "this_is_a_root_chapter"


class Knowledge(Base):
    __tablename__ = "knowledge"
    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bot.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(54))
    date: Mapped[datetime] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(String(4096))
    knowledge_dad_id: Mapped[str] = mapped_column(String(64), index=True)
    children_ref_id: Mapped[str] = mapped_column(String(64))
    indice: Mapped[int] = mapped_column()
    pdf_file: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sqlalchemy.text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sqlalchemy.text("CURRENT_TIMESTAMP")
    )
    vector_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"Chapter(id={self.id!r}, bot_id={self.bot_id!r}, name={self.name!r},  date={self.date!r}, content={self.content!r},knowledge_dad_id={self.knowledge_dad_id!r},indice={self.indice!r},children_ref_id={self.children_ref_id!r}, pdf_file={self.pdf_file!r})"

    def __init__(
        self,
        bot_id: int,
        name: str,
        date: datetime,
        content: str = "empty",
        knowledge_dad_id=ROOT_CHAPTER_ID,
        indice=0,
        children_ref_id="",
        pdf_file: str = "",
    ):
        self.bot_id = bot_id
        self.name = name
        self.date = date
        self.content = content
        self.knowledge_dad_id = knowledge_dad_id
        self.children_ref_id = children_ref_id
        self.indice = indice
        self.pdf_file = pdf_file
