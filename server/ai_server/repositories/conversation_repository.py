from sqlalchemy import delete, select

from ai_server.models import Message, Session
from ai_server.repositories.base import BaseRepository


class ConversationRepository(BaseRepository):
    """Chat sessions and their messages. Only what already-migrated
    aggregates need so far; message_svc.py still queries them directly."""

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
