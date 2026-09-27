from ai_server.services.langchain_facade import ChatTurn, LangChainFacade
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.config.config import app_config
from ai_server.services.prompt_svc import PromptService
from typing import AsyncIterator, Callable
from ai_server.services.message_svc import MessageService
from ai_server.dto.message_dto import MessageDto
import json
import time
import asyncio
from collections import OrderedDict

# Cap on how many (bot_id, user_id) chat histories RagService keeps in
# memory at once. Without this, self.store below grows for the life of the
# process -- one entry per pair that has ever chatted, never evicted.
MAX_CACHED_SESSIONS = 500

# ===== LOGGERS INIT =====
logger = BotFactoryLogger()


class RagService:
    """One conversation turn around the RAG pipeline: persists the
    question and the answer (MessageService), keeps each conversation's
    history cached in memory, and delegates the answer itself to
    LangChainFacade -- this class never touches LangChain directly."""

    def __init__(
        self,
        langchain_facade: LangChainFacade,
        prompt_service: PromptService,
        message_service: MessageService,
    ):
        self.langchain_facade = langchain_facade
        self.prompt_service = prompt_service
        self.message_service = message_service
        self.language = "french"
        self.config = app_config
        # LRU-ish cache of in-memory chat histories, keyed by "bot_id_user_id".
        # OrderedDict so the least-recently-used entry can be evicted once
        # MAX_CACHED_SESSIONS is exceeded (see get_session_history below).
        self.store: "OrderedDict[str, list[ChatTurn]]" = OrderedDict()
        # Guards the check-then-load-then-insert below: two concurrent
        # requests for the same new key would otherwise both miss the cache
        # and both hit the DB, with the second load silently discarding the
        # first (one RagService per app -- see dependencies/services.py -- so
        # self.store is shared by every in-flight request).
        self._store_lock = asyncio.Lock()

    async def get_session_history(self, bot_id: int, user_id: int) -> list[ChatTurn]:
        key = f"{bot_id}_{user_id}"
        async with self._store_lock:
            if key in self.store:
                self.store.move_to_end(key)
                return self.store[key]
            history = await self.load_session_history(bot_id, user_id)
            self.store[key] = history
            if len(self.store) > MAX_CACHED_SESSIONS:
                self.store.popitem(last=False)
            return history

    async def ask(self, bot_id: int, user_id: int, query: str, hide: bool = False):
        logger.debug(f"RAG query for bot {bot_id}, user {user_id}")
        start = time.perf_counter()
        try:
            await self.message_service.save_message(
                bot_id, user_id, "user", query, hide
            )
            bot_prompt = await self.prompt_service.get_bot_prompt(bot_id)
            history = await self.get_session_history(bot_id, user_id)
            result = await self.langchain_facade.answer(
                bot_id, bot_prompt, query, list(history), user_id
            )
            self._record_turn(history, query, result)
            await self.message_service.save_message(
                bot_id, user_id, "assistant", result
            )
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.exception(
                f"RAG ask failed for bot_id={bot_id} user_id={user_id} after {elapsed_ms}ms: {e}"
            )
            raise
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            f"RAG ask succeeded for bot_id={bot_id} user_id={user_id} "
            f"answer_length={len(result)} in {elapsed_ms}ms"
        )
        return result

    async def ask_with_stream(
        self,
        bot_id: int,
        user_id,
        data: str,
        query: str,
        hide: bool = False,
        session_id: int = -1,
    ) -> Callable:
        logger.debug(
            f"RAG streaming query for bot {bot_id}, user {user_id}, session {session_id}"
        )
        await self.message_service.save_message(bot_id, user_id, "user", query, hide)
        bot_prompt = await self.prompt_service.get_bot_prompt(bot_id)
        history = await self.get_session_history(bot_id, user_id)
        chunks = await self.langchain_facade.stream(
            bot_id, bot_prompt, query, list(history), user_id, session_id
        )

        async def generate() -> AsyncIterator[str]:
            start = time.perf_counter()
            try:
                answer_str = ""
                async for chunk in chunks:
                    answer_str += chunk
                    yield f"data: {json.dumps({'answer': chunk})}\n\n"
                self._record_turn(history, query, answer_str)
                await self.message_service.save_message(
                    bot_id, user_id, "assistant", answer_str
                )
                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
                logger.info(
                    f"RAG streaming completed for bot_id={bot_id} user_id={user_id} "
                    f"session_id={session_id}, response length={len(answer_str)}, "
                    f"in {elapsed_ms}ms"
                )
                yield "data: [DONE]\n\n"

            except Exception as e:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
                logger.exception(
                    f"RAG streaming error for bot_id={bot_id} user_id={user_id} "
                    f"session_id={session_id} after {elapsed_ms}ms: {e}"
                )
                error_data = json.dumps({"error": str(e)})
                yield f"data: {json.dumps(error_data)}\n\n"

        return generate

    def _record_turn(self, history: list[ChatTurn], question: str, answer: str) -> None:
        """Append the finished question/answer pair to the cached history.
        Callers hand the facade a copy (list(history)), so appending here
        never mutates a history a running chain is still reading."""
        history.append(ChatTurn("user", question))
        history.append(ChatTurn("assistant", answer))

    # Function to load chat history
    async def load_session_history(self, bot_id: int, user_id: int) -> list[ChatTurn]:
        """Reload prior turns from MySQL via the DB `Session` row for this
        bot/user pair. Messages are keyed in the DB by the integer
        `Session.id` (see message_svc.py::save_message), not by any
        in-process string key, so that real id has to be looked up first —
        passing a synthetic key straight to `message_service.load_session_history`
        would silently never match and always come back empty."""
        session = await self.message_service.get_session(bot_id, user_id)
        if session is None:
            logger.debug(f"No DB session yet for bot_id={bot_id} user_id={user_id}")
            return []
        messages: list[MessageDto] = await self.message_service.load_session_history(
            session.id
        )
        if messages:
            logger.debug(
                f"Loaded {len(messages)} messages for bot_id={bot_id} "
                f"user_id={user_id} (session_id={session.id})"
            )
        return [ChatTurn(message.role, message.content) for message in messages]
