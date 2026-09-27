"""Facade over the whole "chat with a bot" subsystem.

One conversation turn touches seven services: the user is loaded
(UserAdminService), their right to talk to this bot is checked
(BotService / BotAssignmentService, depending on their role), their
token quota is enforced (TokenTrackingService), the welcome question is
built for a first message (BotParametersService), the DB session is
looked up (MessageService), and only then does the LangChain RAG
pipeline run (RagService). rag_router.py used to inject all seven into
every route and repeat that sequence in each one; it now talks to this
single object instead, and only turns its results into HTTP responses.

Every guard raises ApiError with the exact message/status the routes
returned before, in the same order, so the HTTP contract is unchanged.
"""

import json
import time
from typing import AsyncIterator, Optional

from src.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from src.dto.message_dto import MessageDto
from src.dto.user_dto import UserDto
from src.exceptions.api_error import ApiError
from src.log.bot_factory_logger import BotFactoryLogger
from src.services.bot_assignment_svc import BotAssignmentService
from src.services.bot_parameters_svc import BotParametersService
from src.services.bot_svc import BotService
from src.services.message_svc import MessageService
from src.services.rag_svc import RagService
from src.services.token_tracking_svc import TokenTrackingService
from src.services.user_admin_svc import UserAdminService

logger = BotFactoryLogger()


class ChatFacade:

    def __init__(
        self,
        rag_service: RagService,
        user_admin_service: UserAdminService,
        bot_service: BotService,
        bot_assignment_service: BotAssignmentService,
        bot_parameters_service: BotParametersService,
        message_service: MessageService,
        token_tracking_service: TokenTrackingService,
    ):
        self.rag_service = rag_service
        self.user_admin_service = user_admin_service
        self.bot_service = bot_service
        self.bot_assignment_service = bot_assignment_service
        self.bot_parameters_service = bot_parameters_service
        self.message_service = message_service
        self.token_tracking_service = token_tracking_service

    # ===== PUBLIC API =====

    async def ask(self, user_id, question: str) -> str:
        """Answer `question` with the user's currently selected bot."""
        user = await self._load_user(user_id, "chat")
        bot_id = user.selected_bot_id
        if not bot_id:
            logger.warning(f"chat rejected: user {user_id} has no selected bot")
            raise ApiError("You have to select a bot on the app", status_code=409)
        await self._authorize(user, bot_id, "chat")

        started_at = time.perf_counter()
        response = await self.rag_service.ask(bot_id, user_id, question)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            f"chat succeeded for user_id={user_id} bot_id={bot_id} elapsed_ms={elapsed_ms:.1f}"
        )
        return response

    async def stream(
        self, user_id, raw_bot_id: Optional[str], question: Optional[str], data: str
    ) -> AsyncIterator[str]:
        """Answer `question` with bot `raw_bot_id` as an SSE event stream."""
        user = await self._load_user(user_id, "streamchat")
        if not question or not question.strip():
            logger.warning(f"streamchat rejected: missing question for user {user_id}")
            raise ApiError("Question parameter is required", status_code=400)
        bot_id = self._parse_bot_id(raw_bot_id, "streamchat")
        await self._authorize(user, bot_id, "streamchat")
        parsed_data = self._parse_data(data, "streamchat")

        logger.debug(f"streamchat question length={len(question)}")
        iterator = await self._start_stream(user_id, bot_id, parsed_data, question)
        logger.info(f"streamchat streaming started for user_id={user_id} bot_id={bot_id}")
        return iterator

    async def welcome(self, user_id) -> str:
        """Restart the conversation with the selected bot: wipe its history,
        then return the bot's (hidden-question) welcome message."""
        _user, bot_id, question = await self._prepare_welcome(user_id)
        await self.delete_history(bot_id, user_id)

        started_at = time.perf_counter()
        response = await self.rag_service.ask(bot_id, user_id, question, hide=True)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            f"trigfirstmessage succeeded for user_id={user_id} bot_id={bot_id} elapsed_ms={elapsed_ms:.1f}"
        )
        return response

    async def stream_welcome(self, user_id, data: str) -> AsyncIterator[str]:
        """Streaming counterpart of welcome() -- which, unlike it, keeps the
        existing history (the original route never cleared it here)."""
        _user, bot_id, question = await self._prepare_welcome(user_id)
        parsed_data = self._parse_data(data, "trigfirstmessage")

        iterator = await self._start_stream(
            user_id, bot_id, parsed_data, question, hide=True
        )
        logger.info(f"trigfirstmessage streaming started for user_id={user_id} bot_id={bot_id}")
        return iterator

    async def history(self, bot_id: int, user_id) -> list[MessageDto]:
        """Messages of the user's conversation with `bot_id`, oldest first
        (empty if they never talked)."""
        session = await self.message_service.get_session(bot_id, user_id)
        if session is None:
            logger.info(f"get_session_history({bot_id}) no session")
            return []
        return await self.message_service.load_session_history(session_id=session.id)

    async def delete_history(self, bot_id: int, user_id) -> tuple[int, int] | int:
        """Delete the user's conversation with `bot_id`. Returns
        MessageService.delete_session_history()'s (messages, sessions)
        tuple, or a bare 0 when there was no session at all -- the exact
        values the DELETE routes have always put in "deleted_message_count"."""
        logger.info(f"User {user_id} deleting session history for bot {bot_id}")
        session = await self.message_service.get_session(bot_id, user_id)
        if session is None:
            logger.info(f"_delete_session_history({bot_id}) no session")
            return 0
        deleted = await self.message_service.delete_session_history(session.id)
        logger.info(
            f"_delete_session_history({bot_id}) succeeded deleted_message_count={deleted}"
        )
        return deleted

    async def delete_selected_bot_history(self, user_id) -> tuple[int, int] | int:
        """delete_history() for the user's currently selected bot."""
        user = await self._load_user(user_id, "delete_selected_bot_session_history")
        if not user.selected_bot_id:
            logger.warning(
                f"delete_selected_bot_session_history rejected: user {user_id} has no selected bot"
            )
            raise ApiError("Bot_id is required", status_code=400)
        return await self.delete_history(int(user.selected_bot_id), user_id)

    # ===== INTERNAL STEPS =====

    async def _load_user(self, user_id, action: str) -> UserDto:
        user = await self.user_admin_service.get_user_dto_by_id(user_id)
        if not user:
            logger.warning(f"{action} rejected: user {user_id} not found")
            raise ApiError("User not found", status_code=401)
        return user

    def _parse_bot_id(self, bot_id, action: str) -> int:
        if not bot_id:
            logger.warning(f"{action} rejected: missing bot_id")
            raise ApiError("Bot_id is required", status_code=400)
        try:
            return int(bot_id)
        except ValueError:
            logger.warning(f"{action} rejected: invalid bot_id format {bot_id!r}")
            raise ApiError("Invalid bot_id format", status_code=400)

    def _parse_data(self, data: str, action: str) -> dict:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.warning(f"{action} rejected: invalid JSON in data parameter")
            raise ApiError("Invalid JSON in data parameter", status_code=400)

    async def _authorize(self, user: UserDto, bot_id: int, action: str) -> None:
        """Access check, then token quota: both must pass before any LLM call."""
        if not await self._can_access_bot(user, bot_id):
            logger.warning(f"{action} forbidden: user {user.id} has no access to bot {bot_id}")
            raise ApiError(
                f"You don't have permission to access bot {bot_id}", status_code=403
            )
        await self._enforce_token_quota(user)

    async def _can_access_bot(self, user: UserDto, bot_id: int) -> bool:
        if user.roles == ADMIN_ROLE:
            return True
        elif user.roles == USER_ROLE:
            return await self.bot_service.is_bot_belong_to_user(bot_id, user.id)
        elif user.roles == GUEST_ROLE:
            return await self.bot_assignment_service.is_bot_assigned_to_user(
                bot_id, user.id
            )
        return False

    async def _enforce_token_quota(self, user: UserDto) -> None:
        """Refuse with a 429 once the user's billed account has reached
        TOKEN_LIMIT_PER_USER_24H (see TokenTrackingService.get_token_quota).
        Checked before the LLM call, so the request that crosses the limit
        is still served in full: this is a soft cap, not an exact one."""
        quota = await self.token_tracking_service.get_token_quota(user)
        if quota["exceeded"]:
            logger.warning(
                f"LLM call rejected: user {user.id} (billed to {quota['billed_user_id']}) "
                f"used {quota['used_24h']}/{quota['limit_24h']} tokens in the last 24h"
            )
            raise ApiError(
                f"Token limit reached ({quota['limit_24h']} tokens per 24h). Please try again later.",
                status_code=429,
            )

    async def _prepare_welcome(self, user_id) -> tuple[UserDto, int, str]:
        user = await self._load_user(user_id, "trigfirstmessage")
        bot_id = self._parse_bot_id(user.selected_bot_id, "trigfirstmessage")
        await self._authorize(user, bot_id, "trigfirstmessage")
        question = await self.bot_parameters_service.get_welcome_message(
            user.name, bot_id
        )
        return user, bot_id, question

    async def _start_stream(
        self, user_id, bot_id: int, parsed_data: dict, question: str, hide: bool = False
    ) -> AsyncIterator[str]:
        session = await self.message_service.get_session(bot_id, user_id)
        generate = await self.rag_service.ask_with_stream(
            bot_id,
            user_id,
            parsed_data,
            question,
            hide=hide,
            session_id=session.id if session else -1,
        )
        return generate()
