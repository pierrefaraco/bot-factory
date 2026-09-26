from typing import Optional, Sequence, Union

from sqlalchemy import delete, select

from ai_server.models import Message, Session
from ai_server.repositories.base import BaseRepository


class ConversationRepository(BaseRepository):
    """Chat sessions (one per bot + user) and their messages."""

    def add(self, row: Union[Session, Message]) -> None:
        self.session.add(row)

    async def get_session(self, bot_id: int, user_id: int) -> Optional[Session]:
        stmt = select(Session).where(
            Session.bot_id == bot_id, Session.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def last_message(self, session_id: int) -> Optional[Message]:
        """Highest `order` of the session, hidden messages included."""
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.order.desc())
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_visible_messages(self, session_id: int) -> Sequence[Message]:
        """Non-hidden messages, in conversation order."""
        stmt = (
            select(Message)
            .where(Message.session_id == session_id, Message.hide.is_(False))
            .order_by(Message.order.asc())
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def delete_messages(self, session_id: int) -> int:
        """Returns the number of deleted messages."""
        result = await self.session.execute(
            delete(Message).where(Message.session_id == session_id)
        )
        return result.rowcount

    async def delete_session(self, session_id: int) -> int:
        """Returns the number of deleted sessions. Its messages must be
        deleted first (they reference session_id)."""
        result = await self.session.execute(
            delete(Session).where(Session.id == session_id)
        )
        return result.rowcount

    async def delete_for_user(self, user_id: int) -> int:
        """Every session of user_id and their messages (messages first:
        they reference session_id). Returns the number of sessions."""
        session_ids = list(
            (
                await self.session.execute(
                    select(Session.id).where(Session.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
        if session_ids:
            await self.session.execute(
                delete(Message).where(Message.session_id.in_(session_ids))
            )
        await self.session.execute(delete(Session).where(Session.user_id == user_id))
        return len(session_ids)
