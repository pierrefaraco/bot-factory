from ai_server.services.llm_svc import LlmService
from ai_server.services.chroma_db_svc import ChromaDbService
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.config.config import flask_config
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.prompt_svc import PromptService
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from ai_server.decorators.singleton import singleton
from typing import Iterator, Callable
from ai_server.services.message_svc import MessageService
import langchain
import json
from langchain_core.runnables.history import RunnableWithMessageHistory

# Fixed: moved to langchain_classic
try:
    from langchain_classic.chains import (
        create_history_aware_retriever,
        create_retrieval_chain,
    )
    from langchain_classic.chains.combine_documents import create_stuff_documents_chain
except ImportError:
    # Fallback if langchain_classic is not available
    from langchain_community.chains import (
        create_history_aware_retriever,
        create_retrieval_chain,
    )
    from langchain_community.chains.combine_documents import (
        create_stuff_documents_chain,
    )
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from ai_server.dao.database import Session, Message, db
from sqlalchemy.exc import SQLAlchemyError
import time

langchain.debug = False


# ===== LOGGERS INIT =====
logger = BotFactoryLogger()
message_service = MessageService()


@singleton
class RagService:
    def __init__(self):
        self._llm_service = None
        self._db_service = None
        self._prompt_service = None
        self.language = "french"
        self.config = flask_config
        self.store = {}

    @property
    def llm_service(self):
        if self._llm_service is None:
            self._llm_service = LlmService()
        return self._llm_service

    @property
    def db_service(self):
        if self._db_service is None:
            self._db_service = ChromaDbService()
        return self._db_service

    @property
    def prompt_service(self):
        if self._prompt_service is None:
            self._prompt_service = PromptService()
        return self._prompt_service

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

    def build(
        self, bot_id, user_id=None, session_id=None
    ) -> RunnableWithMessageHistory:
        """Assemble a fresh conversational RAG chain for one question.

        Rebuilt on every call rather than cached on `self`: each call needs
        its own TokenCountingCallback (tied to this user_id/bot_id/session_id)
        and the singleton RagService is shared across concurrent requests, so
        the built chain is returned instead of stored as instance state.

        Steps below are numbered to match the diagram in
        server/doc/LANGCHAIN_ARCHITECTURE.md#3.
        """
        start = time.perf_counter()

        # The LLM is invoked twice per question: once to reformulate it (step
        # ①), once to draft the answer (step ③). Each call needs its own
        # ChatMistralAI instance since get_llm() attaches a fresh
        # TokenCountingCallback every time (see llm_svc.py).
        reformulating_llm = self.llm_service.get_llm(
            user_id=user_id, bot_id=bot_id, session_id=session_id
        )
        answering_llm = self.llm_service.get_llm(
            user_id=user_id, bot_id=bot_id, session_id=session_id
        )
        retriever = self.db_service.get_retriever()
        contextualize_prompt = self.prompt_service.contextualize_q_prompt
        qa_prompt = self.prompt_service.get_qa_prompt(bot_id)

        history_aware_retriever = self._build_history_aware_retriever(
            reformulating_llm, retriever, contextualize_prompt
        )
        answer_chain = self._build_answer_chain(answering_llm, qa_prompt)
        rag_chain = self._build_retrieval_chain(history_aware_retriever, answer_chain)
        conversational_rag_chain = self._wrap_with_history(rag_chain)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.debug(
            f"RAG chain built for bot_id={bot_id} user_id={user_id} "
            f"session_id={session_id} in {elapsed_ms}ms"
        )
        return conversational_rag_chain

    def _build_history_aware_retriever(self, llm, retriever, contextualize_prompt):
        """Step ① + ②: reformulate the question using chat history, retrieve
        matching chunks, then label each chunk with its source chapter."""
        return create_history_aware_retriever(
            llm, retriever, contextualize_prompt
        ) | RunnableLambda(self._label_documents_with_source)

    def _build_answer_chain(self, llm, qa_prompt):
        """Step ③: stuff the labeled documents into the bot's system prompt
        and draft the final answer."""
        return create_stuff_documents_chain(llm, qa_prompt)

    def _build_retrieval_chain(self, history_aware_retriever, answer_chain):
        """Step ④: glue steps ①-③ into one chain exposing 'answer'/'context'."""
        return create_retrieval_chain(history_aware_retriever, answer_chain)

    def _wrap_with_history(self, rag_chain) -> RunnableWithMessageHistory:
        """Step ⑤: read/write chat_history around rag_chain via
        get_session_history, keyed by the caller-supplied session_id."""
        return RunnableWithMessageHistory(
            rag_chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = self.load_session_history(session_id)
        return self.store[session_id]

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

    def ask(self, bot_id: int, user_id: int, query: str, hide: bool = False):
        logger.debug(f"RAG query for bot {bot_id}, user {user_id}")
        start = time.perf_counter()
        try:
            collection_name = f"Collection{bot_id}"
            self.db_service.build(collection_name)
            # Passer user_id pour activer le tracking de tokens
            conversational_rag_chain = self.build(bot_id, user_id=user_id)
            result = self.invoke_and_save(
                conversational_rag_chain, bot_id, user_id, query, hide
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

    def ask_with_stream(
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
        collection_name = f"Collection{bot_id}"
        message_service.save_message(bot_id, user_id, "user", query, hide)
        self.db_service.build(collection_name)
        # Ensure the collection is built before invoking the chain
        # Passer user_id pour activer le tracking de tokens
        conversational_rag_chain = self.build(
            bot_id, user_id=user_id, session_id=session_id
        )

        def generate() -> Iterator[str]:
            start = time.perf_counter()
            try:
                answer_str = ""
                chunk_iterator = conversational_rag_chain.stream(
                    {"input": query},
                    config={"configurable": {"session_id": collection_name}},
                )
                for chunk in chunk_iterator:
                    if "answer" in chunk and chunk["answer"]:
                        answer = chunk["answer"]
                        answer_str += answer
                        yield f"data: {json.dumps({'answer': answer})}\n\n"
                message_service.save_message(bot_id, user_id, "assistant", answer_str)
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

    def invoke_and_save(
        self, conversational_rag_chain, bot_id, user_id, input_text, hide: bool = False
    ) -> str:
        # Save the user question with role "human"
        message_service.save_message(bot_id, user_id, "user", input_text, hide)

        # Get the AI response
        logger.debug(f"Invoking RAG chain for bot_id={bot_id} user_id={user_id}")
        start = time.perf_counter()
        result = conversational_rag_chain.invoke(
            {"input": input_text},
            config={"configurable": {"session_id": f"{bot_id}_{user_id}"}},
        )["answer"]
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            f"RAG chain invocation succeeded for bot_id={bot_id} user_id={user_id} "
            f"answer_length={len(result)} in {elapsed_ms}ms"
        )

        # Save the AI answer with role "ai"
        message_service.save_message(bot_id, user_id, "assistant", result)
        return result

    # Function to load chat history
    def load_session_history(self, session_id: str) -> BaseChatMessageHistory:
        chat_history = ChatMessageHistory()
        try:
            messages: list[Message] = message_service.load_session_history(session_id)
            if messages:
                logger.debug(
                    f"Loaded {len(messages)} messages for session {session_id}"
                )
                for message in messages:
                    chat_history.add_message(
                        {"role": message.role, "content": message.content}
                    )
        except SQLAlchemyError as e:
            logger.exception(f"Failed to load session history for {session_id}: {e}")
        finally:
            db.session.close()
        return chat_history
