from datetime import datetime
from typing import Optional

from ai_server.models import Session, Message
from ai_server.dto.message_dto import MessageDto
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.repositories import ConversationRepository

logger = BotFactoryLogger()


class MessageService:
    """Chat sessions and their messages. No manual rollback/close here --
    same convention as the other services: a failure propagates up to the
    request's own async_db_session_scope() teardown instead of being
    swallowed here."""

    def __init__(self, conversation_repo: ConversationRepository):
        self.conversation_repo = conversation_repo

    async def get_session(self, bot_id: int, user_id: int) -> Optional[Session]:
        return await self.conversation_repo.get_session(bot_id, user_id)

    async def save_message(
        self, bot_id: int, user_id: int, role: str, content: str, hide: bool = False
    ) -> None:
        """Append a message to the bot + user session, creating the session
        on the first message -- in one transaction."""
        # content is raw chat text (may contain user PII): never logged in full,
        # only its length.
        logger.info(
            f"save_message bot_id={bot_id} user_id={user_id} role={role} "
            f"content_len={len(content) if content else 0} hide={hide}"
        )
        session = await self.get_session(bot_id, user_id)
        order = 0
        if not session:
            logger.info(f"Creating new session for bot_id={bot_id} user_id={user_id}")
            session = Session(bot_id, user_id)
            self.conversation_repo.add(session)
            await self.conversation_repo.flush()
        else:
            last_message = await self.conversation_repo.last_message(session.id)
            if last_message:
                logger.debug(
                    f"Appending after last_message id={last_message.id} "
                    f"order={last_message.order} session_id={session.id}"
                )
                order = last_message.order + 1

        message = Message(
            order,
            session_id=session.id,
            role=role,
            content=content,
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            hide=hide,
        )
        self.conversation_repo.add(message)
        await self.conversation_repo.commit()
        logger.info(
            f"Message saved id={message.id} session_id={session.id} "
            f"bot_id={bot_id} user_id={user_id} role={role}"
        )

    async def load_session_history(self, session_id) -> list[MessageDto]:
        """Non-hidden messages of the session, in conversation order."""
        msg_list = await self.conversation_repo.list_visible_messages(session_id)
        msg_list_dto = [
            MessageDto(
                msg.id, msg.session_id, msg.role, msg.content, msg.order, msg.time
            )
            for msg in msg_list
        ]
        logger.info(f"Loaded {len(msg_list_dto)} messages for session_id={session_id}")
        return msg_list_dto

    async def delete_session_history(self, session_id) -> tuple[int, int]:
        """Delete the session and its messages; a session without messages
        is left alone and reported as (0, 0).

        Returns:
            (deleted message count, deleted session count)
        """
        deleted_message_count = await self.conversation_repo.delete_messages(session_id)
        if deleted_message_count == 0:
            logger.info(f"No messages found for session_id={session_id}")
            return 0, 0
        deleted_session_count = await self.conversation_repo.delete_session(session_id)
        await self.conversation_repo.commit()
        logger.info(
            f"Deleted {deleted_message_count} messages and "
            f"{deleted_session_count} session for session_id={session_id}"
        )
        return deleted_message_count, deleted_session_count
