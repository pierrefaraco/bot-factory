from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select

from ai_server.dao.database import Session, Message, get_async_session
from ai_server.dto.message_dto import MessageDto
from ai_server.decorators.singleton import singleton
from ai_server.log.bot_factory_logger import BotFactoryLogger

logger = BotFactoryLogger()


@singleton
class MessageService:
    """Async throughout: the only callers (rag_svc.py, rag_router.py) are
    both migrated together. No manual rollback/close here -- same convention
    as the other async-migrated services (bot_svc.py, user_admin_svc.py,
    ...): a failure propagates up to the request's own
    async_db_session_scope() teardown instead of being swallowed here."""

    async def get_session(self, bot_id: int, user_id: int) -> Optional[Session]:
        session_db = get_async_session()
        result = await session_db.execute(
            select(Session).where(Session.bot_id == bot_id, Session.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def save_message(
        self, bot_id: int, user_id: int, role: str, content: str, hide: bool = False
    ) -> None:
        # content is raw chat text (may contain user PII): never logged in full,
        # only its length.
        logger.info(
            f"save_message bot_id={bot_id} user_id={user_id} role={role} "
            f"content_len={len(content) if content else 0} hide={hide}"
        )
        session_db = get_async_session()
        session = await self.get_session(bot_id, user_id)

        if not session:
            logger.info(f"Creating new session for bot_id={bot_id} user_id={user_id}")
            session = Session(bot_id, user_id)
            session_db.add(session)
            await session_db.commit()
            await session_db.refresh(session)
            message = Message(
                0,
                session_id=session.id,
                role=role,
                content=content,
                time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                hide=hide,
            )
        else:
            result = await session_db.execute(
                select(Message)
                .where(Message.session_id == session.id)
                .order_by(Message.order.desc())
            )
            last_message: Optional[Message] = result.scalars().first()
            if last_message:
                logger.debug(
                    f"Appending after last_message id={last_message.id} "
                    f"order={last_message.order} session_id={session.id}"
                )
                message = Message(
                    last_message.order + 1,
                    session_id=session.id,
                    role=role,
                    content=content,
                    time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    hide=hide,
                )
            else:
                message = Message(
                    0,
                    session_id=session.id,
                    role=role,
                    content=content,
                    time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    hide=hide,
                )
        session_db.add(message)
        await session_db.commit()
        await session_db.refresh(message)
        logger.info(
            f"Message saved id={message.id} session_id={session.id} "
            f"bot_id={bot_id} user_id={user_id} role={role}"
        )

    async def load_session_history(self, session_id) -> list[MessageDto]:
        session_db = get_async_session()
        result = await session_db.execute(
            select(Message)
            .where(Message.session_id == session_id, Message.hide.is_(False))
            .order_by(Message.order.asc())
        )
        msg_list = result.scalars().all()
        msg_list_dto = [
            MessageDto(msg.id, msg.session_id, msg.role, msg.content, msg.order, msg.time)
            for msg in msg_list
        ]
        logger.info(f"Loaded {len(msg_list_dto)} messages for session_id={session_id}")
        return msg_list_dto

    async def delete_all_users_sessions(self, user_id):
        session_db = get_async_session()
        result = await session_db.execute(select(Session).where(Session.user_id == user_id))
        sessions = result.scalars().all()
        logger.info(f"Deleting {len(sessions)} sessions for user_id={user_id}")
        for session in sessions:
            await self.delete_session_history(session.id)

    async def delete_all_bots_sessions(self, bot_id):
        session_db = get_async_session()
        result = await session_db.execute(select(Session).where(Session.bot_id == bot_id))
        sessions = result.scalars().all()
        logger.info(f"Deleting {len(sessions)} sessions for bot_id={bot_id}")
        for session in sessions:
            await self.delete_session_history(session.id)

    async def delete_session_history(self, session_id) -> tuple[int, int]:
        session_db = get_async_session()
        result = await session_db.execute(
            delete(Message).where(Message.session_id == session_id)
        )
        deleted_message_count = result.rowcount
        if deleted_message_count == 0:
            logger.info(f"No messages found for session_id={session_id}")
            return 0, 0
        result = await session_db.execute(delete(Session).where(Session.id == session_id))
        deleted_session_count = result.rowcount
        await session_db.commit()
        logger.info(
            f"Deleted {deleted_message_count} messages and "
            f"{deleted_session_count} session for session_id={session_id}"
        )
        return deleted_message_count, deleted_session_count
