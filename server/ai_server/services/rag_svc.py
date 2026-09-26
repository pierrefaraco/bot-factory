from ai_server.services.llm_svc import LlmService
from ai_server.services.chroma_db_svc import ChromaDbService
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.log.prompt_debug_logger import PromptDebugLogger
from ai_server.config.config import app_config
from ai_server.services.prompt_svc import PromptService
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from typing import AsyncIterator, Callable
from ai_server.services.message_svc import MessageService
from ai_server.dto.message_dto import MessageDto
from starlette.concurrency import run_in_threadpool
import langchain
import json
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
import time
import asyncio
from collections import OrderedDict

langchain.debug = False

# Cap on how many (bot_id, user_id) chat histories RagService keeps in
# memory at once. Without this, self.store below grows for the life of the
# process -- one entry per pair that has ever chatted, never evicted.
MAX_CACHED_SESSIONS = 500

# ===== LOGGERS INIT =====
logger = BotFactoryLogger()
prompt_debug_logger = PromptDebugLogger()


class RagService:

    def __init__(
        self,
        llm_service: LlmService,
        db_service: ChromaDbService,
        prompt_service: PromptService,
        message_service: MessageService,
    ):
        self.llm_service = llm_service
        self.db_service = db_service
        self.prompt_service = prompt_service
        self.message_service = message_service
        self.language = "french"
        self.config = app_config
        # LRU-ish cache of in-memory chat histories, keyed by "bot_id_user_id".
        # OrderedDict so the least-recently-used entry can be evicted once
        # MAX_CACHED_SESSIONS is exceeded (see get_session_history below).
        self.store: "OrderedDict[str, BaseChatMessageHistory]" = OrderedDict()
        # Guards the check-then-load-then-insert below: two concurrent
        # requests for the same new key would otherwise both miss the cache
        # and both hit the DB, with the second load silently discarding the
        # first (one RagService per app -- see dependencies/services.py -- so
        # self.store is shared by every in-flight request).
        self._store_lock = asyncio.Lock()

    def _label_documents_with_source(self, docs):
        """Prefix each retrieved chunk's page_content with its source
        knowledge chapter's name, when known. Reads from `page_content`
        only (never metadata directly in the prompt template) so chunks
        ingested before "name" existed in Chroma metadata still pass
        through untouched instead of breaking the chain."""
        for doc in docs:
            name = doc.metadata.get("name")
            if name and not doc.page_content.startswith(f"Source: {name}\n"):
                doc.page_content = f"Source: {name}\n{doc.page_content}"
        return docs

    def build(self, bot_id, bot_prompt: str, user_id=None, session_id=None) -> Runnable:
        """Assemble a fresh single-call RAG pipeline for one question, as a
        plain LCEL chain (no create_history_aware_retriever /
        create_retrieval_chain / RunnableWithMessageHistory indirection).

        Rebuilt on every call rather than cached on `self`: each call needs
        its own TokenCountingCallback (tied to this user_id/bot_id/session_id)
        and the app-wide RagService is shared across concurrent requests, so
        the built chain is returned instead of stored as instance state.

        Genuinely blocking under the hood, with no async equivalent:
        db_service.build_retriever() (a real ChromaDB client init). Callers
        (ask()/ask_with_stream()) read bot_prompt on the async session
        first, then run this via run_in_threadpool so it doesn't block the
        event loop.

        Retrieval runs directly on the raw question (no LLM reformulation
        pass) — one LLM call per question instead of two. The trade-off:
        an ambiguous follow-up like "et pour lui ?" is searched against
        Chroma verbatim rather than as a reformulated, self-contained
        question, so retrieval quality on such follow-ups can suffer even
        though the final answer still sees the full chat_history.

        A `prompt_debug_logger.debug` call (PromptDebugLogger, its own
        PROMPT_DEBUG_LVL env var — independent of LOGGER_LVL) is inserted
        between every step up to and including the prompt sent to the LLM,
        so the prompt's construction can be followed end to end without
        turning on full app-wide DEBUG logging — the ①-③ markers below match
        the walkthrough in server/doc/LANGCHAIN_ARCHITECTURE.md#3. There is
        no such step between `llm` and `StrOutputParser()`: a plain
        RunnableLambda there forces LangChain to buffer the LLM's entire
        streamed output into one value before passing it on (it has no
        transform() of its own to chain into `.stream()`'s per-chunk
        pipeline), which silently turned real token-by-token SSE streaming
        back into one single chunk delivered at the end. The ④ raw-answer
        log now happens in ask_with_stream()/invoke_and_save() instead,
        once the full answer is already accumulated — same debug value,
        no chain step in the way.
        """
        llm = self.llm_service.get_llm(
            user_id=user_id, bot_id=bot_id, session_id=session_id
        )
        # build_retriever() (not build()+get_retriever()): ChromaDbService is
        # itself one app-wide instance shared by every concurrent request, and the
        # two-call form only communicates the built retriever back via
        # self.retriever -- two bots' requests can interleave in between and
        # steal each other's retriever. build_retriever() returns it directly
        # instead, from purely local values -- see its own docstring.
        retriever = self.db_service.build_retriever(f"Collection{bot_id}")
        qa_prompt = self.prompt_service.get_qa_prompt(bot_id, bot_prompt)

        return (
            RunnableLambda(self._log_initial_input)
            | RunnableLambda(
                lambda inputs: {
                    **inputs,
                    "context": self._retrieve_and_label_sources(
                        retriever, inputs["input"]
                    ),
                }
            )
            | RunnableLambda(self._log_retrieved_context)
            | RunnablePassthrough.assign(context=lambda x: self._format_docs(x["context"]))
            | RunnableLambda(self._log_formatted_context)
            | qa_prompt
            | RunnableLambda(self._log_final_prompt)
            | llm
            | StrOutputParser()
        )

    def _retrieve_and_label_sources(self, retriever, question: str):
        """Fetch matching chunks for the raw question, then label each one
        with its source knowledge chapter (see _label_documents_with_source)."""
        return self._label_documents_with_source(retriever.invoke(question))

    def _format_docs(self, docs) -> str:
        """Stuff the labeled documents into a single string for the
        {context} slot of the bot's system prompt."""
        return "\n\n".join(doc.page_content for doc in docs)

    def _truncate(self, text, limit: int = 800) -> str:
        """Cap a debug-logged string so a large context/prompt doesn't flood
        the logs; the full value is still what's actually sent/received."""
        text = str(text)
        if len(text) <= limit:
            return text
        return f"{text[:limit]}… [{len(text) - limit} caractères tronqués]"

    def _log_initial_input(self, inputs: dict) -> dict:
        """Q: raw pipeline input, before any processing."""
        history = inputs.get("chat_history", [])
        history_preview = "\n".join(
            f"  [{message.type}] {self._truncate(message.content, 200)}"
            for message in history
        ) or "  (vide)"
        prompt_debug_logger.debug(
            f"Q — input={inputs['input']!r}\n"
            f"chat_history ({len(history)} message(s)):\n{history_preview}"
        )
        return inputs

    def _log_retrieved_context(self, inputs: dict) -> dict:
        """① chunks retrieved from Chroma and labeled with their source,
        before they get stuffed into a single {context} string."""
        docs = inputs["context"]
        previews = "\n---\n".join(
            self._truncate(doc.page_content, 300) for doc in docs
        )
        prompt_debug_logger.debug(f"① {len(docs)} chunk(s) retrieved:\n{previews}")
        return inputs

    def _log_formatted_context(self, inputs: dict) -> dict:
        """② the {context} slot after RunnablePassthrough.assign has
        collapsed the document list into one string."""
        prompt_debug_logger.debug(
            f"② context formatted for {{context}}:\n{self._truncate(inputs['context'])}"
        )
        return inputs

    def _log_final_prompt(self, prompt_value):
        """③ the exact list of messages (system/chat_history/human) about
        to be sent to the LLM, i.e. the fully assembled prompt."""
        messages = "\n".join(
            f"[{message.type}] {self._truncate(message.content)}"
            for message in prompt_value.to_messages()
        )
        prompt_debug_logger.debug(f"③ final prompt sent to LLM:\n{messages}")
        return prompt_value

    def _log_llm_answer(self, answer: str) -> None:
        """④ the LLM's full answer, already reassembled from
        StrOutputParser's chunks (streaming) or returned whole (invoke) —
        called from outside the chain so it can't block `.stream()`."""
        prompt_debug_logger.debug(f"④ raw LLM answer: {self._truncate(answer)}")

    async def get_session_history(self, bot_id: int, user_id: int) -> BaseChatMessageHistory:
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

    def ingest_pdf(self, pdf_file_path: str, collection_name="MY_COLLECTION"):
        logger.info(f"Ingesting PDF '{pdf_file_path}' into collection={collection_name}")
        start = time.perf_counter()
        try:
            self.db_service.ingest(pdf_file_path, collection_name)
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.exception(
                f"PDF ingestion failed for '{pdf_file_path}' collection={collection_name} "
                f"after {elapsed_ms}ms: {e}"
            )
            raise
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            f"PDF ingestion succeeded for '{pdf_file_path}' collection={collection_name} "
            f"in {elapsed_ms}ms"
        )

    def ingest_directory(self, pdf_directory: str, collection_name="MY_COLLECTION"):
        logger.info(f"Ingesting directory '{pdf_directory}' into collection={collection_name}")
        start = time.perf_counter()
        try:
            self.db_service.ingest_directory(pdf_directory, collection_name)
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.exception(
                f"Directory ingestion failed for '{pdf_directory}' collection={collection_name} "
                f"after {elapsed_ms}ms: {e}"
            )
            raise
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            f"Directory ingestion succeeded for '{pdf_directory}' collection={collection_name} "
            f"in {elapsed_ms}ms"
        )

    async def ask(self, bot_id: int, user_id: int, query: str, hide: bool = False):
        logger.debug(f"RAG query for bot {bot_id}, user {user_id}")
        start = time.perf_counter()
        try:
            # build() is called via run_in_threadpool, not awaited directly:
            # it's still genuinely blocking under the hood (ChromaDB client
            # init in db_service.build_retriever()), with no async
            # equivalent -- see build()'s own docstring. The bot prompt is
            # read beforehand, on the async session.
            bot_prompt = await self.prompt_service.get_bot_prompt(bot_id)
            rag_chain = await run_in_threadpool(self.build, bot_id, bot_prompt, user_id)
            result = await self.invoke_and_save(rag_chain, bot_id, user_id, query, hide)
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
        rag_chain = await run_in_threadpool(
            self.build, bot_id, bot_prompt, user_id, session_id
        )
        history = await self.get_session_history(bot_id, user_id)

        async def generate() -> AsyncIterator[str]:
            start = time.perf_counter()
            try:
                answer_str = ""
                chunk_iterator = rag_chain.astream(
                    {"input": query, "chat_history": history.messages}
                )
                async for chunk in chunk_iterator:
                    if chunk:
                        answer_str += chunk
                        yield f"data: {json.dumps({'answer': chunk})}\n\n"
                self._log_llm_answer(answer_str)
                history.add_user_message(query)
                history.add_ai_message(answer_str)
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

    async def invoke_and_save(
        self, rag_chain: Runnable, bot_id, user_id, input_text, hide: bool = False
    ) -> str:
        # Save the user question with role "human"
        await self.message_service.save_message(
            bot_id, user_id, "user", input_text, hide
        )

        # Get the AI response
        logger.debug(f"Invoking RAG chain for bot_id={bot_id} user_id={user_id}")
        start = time.perf_counter()
        history = await self.get_session_history(bot_id, user_id)
        result = await rag_chain.ainvoke(
            {"input": input_text, "chat_history": history.messages}
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            f"RAG chain invocation succeeded for bot_id={bot_id} user_id={user_id} "
            f"answer_length={len(result)} in {elapsed_ms}ms"
        )
        self._log_llm_answer(result)
        history.add_user_message(input_text)
        history.add_ai_message(result)

        # Save the AI answer with role "ai"
        await self.message_service.save_message(bot_id, user_id, "assistant", result)
        return result

    # Function to load chat history
    async def load_session_history(self, bot_id: int, user_id: int) -> BaseChatMessageHistory:
        """Reload prior turns from MySQL via the DB `Session` row for this
        bot/user pair. Messages are keyed in the DB by the integer
        `Session.id` (see message_svc.py::save_message), not by any
        in-process string key, so that real id has to be looked up first —
        passing a synthetic key straight to `message_service.load_session_history`
        would silently never match and always come back empty."""
        chat_history = ChatMessageHistory()
        session = await self.message_service.get_session(bot_id, user_id)
        if session is None:
            logger.debug(f"No DB session yet for bot_id={bot_id} user_id={user_id}")
            return chat_history
        messages: list[MessageDto] = await self.message_service.load_session_history(
            session.id
        )
        if messages:
            logger.debug(
                f"Loaded {len(messages)} messages for bot_id={bot_id} "
                f"user_id={user_id} (session_id={session.id})"
            )
            for message in messages:
                # add_message({"role": ..., "content": ...}) looked
                # equivalent but isn't: ChatMessageHistory.add_message()
                # does no coercion, so it stored raw dicts instead of
                # HumanMessage/AIMessage — anything reading
                # chat_history.messages downstream (e.g. message.type)
                # blew up with AttributeError as soon as history was
                # actually non-empty.
                if message.role == "assistant":
                    chat_history.add_ai_message(message.content)
                else:
                    chat_history.add_user_message(message.content)
        return chat_history
