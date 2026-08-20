from datetime import datetime
from ai_server.dao.database import Session, Message, db
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_
from ai_server.dto.message_dto import MessageDto
from ai_server.decorators.singleton import singleton
from ai_server.log.bot_factory_logger import BotFactoryLogger

logger = BotFactoryLogger()


@singleton
class MessageService:
    def get_session(self, bot_id: int, user_id: int) -> Session:
        try:
            # Check if the session already exists

            session = Session.query.filter_by(bot_id=bot_id, user_id=user_id).first()
            return session
        except SQLAlchemyError:
            logger.exception(f"DB error getting session bot_id={bot_id} user_id={user_id}")
            db.session.rollback()
        finally:
            db.session.close()

    def save_message(
        self, bot_id: int, user_id: int, role: str, content: str, hide: bool = False
    ) -> None:
        # content is raw chat text (may contain user PII): never logged in full,
        # only its length.
        logger.info(
            f"save_message bot_id={bot_id} user_id={user_id} role={role} "
            f"content_len={len(content) if content else 0} hide={hide}"
        )
        try:
            # Check if the sessueryion already exists
            session = self.get_session(bot_id, user_id)

            if not session:
                logger.info(
                    f"Creating new session for bot_id={bot_id} user_id={user_id}"
                )
                # Create a new session if it doesn't exist
                session = Session(bot_id, user_id)
                db.session.add(session)
                db.session.commit()
                db.session.refresh(session)
                message = Message(
                    0,
                    session_id=session.id,
                    role=role,
                    content=content,
                    time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    hide=hide,
                )
            else:
                last_message: Message = (
                    Message.query.filter_by(session_id=session.id)
                    .order_by(Message.order.desc())
                    .first()
                )
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
            db.session.add(message)
            db.session.commit()
            db.session.refresh(message)
            logger.info(
                f"Message saved id={message.id} session_id={session.id} "
                f"bot_id={bot_id} user_id={user_id} role={role}"
            )

        except SQLAlchemyError:
            logger.exception(f"DB error saving message bot_id={bot_id} user_id={user_id}")
            db.session.rollback()
        finally:
            db.session.close()

    def load_session_history(self, session_id) -> list[Message]:
        try:
            # def __init__(self, id: str, session_id:int,  role: str, content: str, order: int,time:str):
            msg_list: list[Message] = (
                Message.query.filter_by(session_id=session_id, hide=0)
                .order_by(Message.order.asc())
                .all()
            )
            msg_list_dto = [
                MessageDto(
                    msg.id, msg.session_id, msg.role, msg.content, msg.order, msg.time
                )
                for msg in msg_list
            ]
            logger.info(
                f"Loaded {len(msg_list_dto)} messages for session_id={session_id}"
            )
            return msg_list_dto
        except SQLAlchemyError:
            logger.exception(f"DB error loading session history for session_id={session_id}")
        finally:
            db.session.close()

    def delete_all_users_sessions(self, user_id):
        sessions: list[Session] = Session.query.filter_by(user_id=user_id).all()
        logger.info(f"Deleting {len(sessions)} sessions for user_id={user_id}")
        for session in sessions:
            self.delete_session_history(session.id)

    def delete_all_bots_sessions(self, bot_id):
        sessions: list[Session] = Session.query.filter_by(bot_id=bot_id).all()
        logger.info(f"Deleting {len(sessions)} sessions for bot_id={bot_id}")
        for session in sessions:
            self.delete_session_history(session.id)

    def delete_session_history(self, session_id) -> tuple[int, int]:
        try:
            deleted_message_count = Message.query.filter_by(
                session_id=session_id
            ).delete()
            if deleted_message_count == 0:
                logger.info(f"No messages found for session_id={session_id}")
                return 0, 0
            deleted_session_count = Session.query.filter_by(id=session_id).delete()
            db.session.commit()
            logger.info(
                f"Deleted {deleted_message_count} messages and "
                f"{deleted_session_count} session for session_id={session_id}"
            )
            return deleted_message_count, deleted_session_count
        except SQLAlchemyError:
            logger.exception(f"DB error deleting session history for session_id={session_id}")
            db.session.rollback()
            return 0, 0
        finally:
            db.session.close()
