from ai_server.services.llm_svc import LlmService
from ai_server.services.chroma_db_svc import ChromaDbService
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.config.config import app_config
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.prompt_svc import PromptService
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from ai_server.decorators.singleton import singleton
from typing import Iterator, Callable
from ai_server.services.message_svc import MessageService
import langchain
import json
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
        self.config = app_config
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

    def build(self, bot_id, user_id=None, session_id=None) -> Runnable:
        """Assemble a fresh single-call RAG pipeline for one question, as a
        plain LCEL chain (no create_history_aware_retriever /
        create_retrieval_chain / RunnableWithMessageHistory indirection).

        Rebuilt on every call rather than cached on `self`: each call needs
        its own TokenCountingCallback (tied to this user_id/bot_id/session_id)
        and the singleton RagService is shared across concurrent requests, so
        the built chain is returned instead of stored as instance state.

        Retrieval runs directly on the raw question (no LLM reformulation
        pass) — one LLM call per question instead of two. The trade-off:
        an ambiguous follow-up like "et pour lui ?" is searched against
        Chroma verbatim rather than as a reformulated, self-contained
        question, so retrieval quality on such follow-ups can suffer even
        though the final answer still sees the full chat_history.
        """
        llm = self.llm_service.get_llm(
            user_id=user_id, bot_id=bot_id, session_id=session_id
        )
        retriever = self.db_service.get_retriever()
        qa_prompt = self.prompt_service.get_qa_prompt(bot_id)

        return (
            RunnableLambda(
                lambda inputs: {
                    **inputs,
                    "context": self._retrieve_and_label_sources(
                        retriever, inputs["input"]
                    ),
                }
            )
            | RunnablePassthrough.assign(context=lambda x: self._format_docs(x["context"]))
            | qa_prompt
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
            rag_chain = self.build(bot_id, user_id=user_id)
            result = self.invoke_and_save(rag_chain, bot_id, user_id, query, hide)
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
        rag_chain = self.build(bot_id, user_id=user_id, session_id=session_id)
        history = self.get_session_history(collection_name)

        def generate() -> Iterator[str]:
            start = time.perf_counter()
            try:
                answer_str = ""
                chunk_iterator = rag_chain.stream(
                    {"input": query, "chat_history": history.messages}
                )
                for chunk in chunk_iterator:
                    if chunk:
                        answer_str += chunk
                        yield f"data: {json.dumps({'answer': chunk})}\n\n"
                history.add_user_message(query)
                history.add_ai_message(answer_str)
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
        self, rag_chain: Runnable, bot_id, user_id, input_text, hide: bool = False
    ) -> str:
        # Save the user question with role "human"
        message_service.save_message(bot_id, user_id, "user", input_text, hide)

        # Get the AI response
        logger.debug(f"Invoking RAG chain for bot_id={bot_id} user_id={user_id}")
        start = time.perf_counter()
        history = self.get_session_history(f"{bot_id}_{user_id}")
        result = rag_chain.invoke(
            {"input": input_text, "chat_history": history.messages}
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            f"RAG chain invocation succeeded for bot_id={bot_id} user_id={user_id} "
            f"answer_length={len(result)} in {elapsed_ms}ms"
        )
        history.add_user_message(input_text)
        history.add_ai_message(result)

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
