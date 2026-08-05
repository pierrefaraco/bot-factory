from ai_server.services.llm_svc import LlmService
from ai_server.services.chroma_db_svc import ChromaDbService
from ai_server.log.app_logger import AppLogger
from ai_server.config.config import flask_config
from ai_server.log.app_logger import AppLogger
from ai_server.services.prompt_svc import PromptService
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
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
from ai_server.api_controllers.rest_bot_parameters import bot_parameters_svc

langchain.debug = False


# ===== LOGGERS INIT =====
logger = AppLogger()
message_service = MessageService()


@singleton
class RagService:
    def __init__(self):
        self._llm_service = None
        self._db_service = None
        self._prompt_service = None
        self.rag_chain = None
        self.language = "french"
        self.config = flask_config
        self.store = {}
        self.conversational_rag_chain = None

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

    def build(self, bot_id, user_id=None, session_id=None):
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # Passer user_id et bot_id pour activer le tracking de tokens
        llm = self.llm_service.get_llm(
            user_id=user_id, bot_id=bot_id, session_id=session_id
        )
        prompt = self.prompt_service.contextualize_q_prompt
        retriever = self.db_service.get_retriever()
        history_aware_retriever = create_history_aware_retriever(llm, retriever, prompt)
        question_answer_chain = create_stuff_documents_chain(
            self.llm_service.get_llm(
                user_id=user_id, bot_id=bot_id, session_id=session_id
            ),
            self.prompt_service.get_qa_promt(bot_id),
        )
        self.rag_chain = create_retrieval_chain(
            history_aware_retriever, question_answer_chain
        )
        self.conversational_rag_chain = RunnableWithMessageHistory(
            self.rag_chain,
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
        self.db_service.ingest(pdf_file_path, collection_name)

    def ingest_directory(self, pdf_directory: str, collection_name="MY_COLLECTION"):
        self.db_service.ingest_directory(pdf_directory, collection_name)

    def ask(self, bot_id: int, user_id: int, query: str, hide: bool = False):
        logger.debug(f"RAG query for bot {bot_id}, user {user_id}")
        collection_name = f"Collection{bot_id}"
        self.db_service.build(collection_name)
        # Passer user_id pour activer le tracking de tokens
        self.build(bot_id, user_id=user_id)
        return self.invoke_and_save(bot_id, user_id, query, hide)

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
        self.build(bot_id, user_id=user_id, session_id=session_id)

        def generate(data) -> Iterator[str]:
            try:
                answer_str = ""
                chunk_iterator = self.conversational_rag_chain.stream(
                    {"input": query},
                    config={"configurable": {"session_id": collection_name}},
                )
                for chunk in chunk_iterator:
                    if "answer" in chunk and chunk["answer"]:
                        answer = chunk["answer"]
                        answer_str += answer
                        yield f"data: {json.dumps({'answer': answer})}\n\n"
                message_service.save_message(bot_id, user_id, "assistant", answer_str)
                logger.debug(
                    f"RAG streaming completed for bot {bot_id}, response length: {len(answer_str)}"
                )
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"RAG streaming error for bot {bot_id}: {e}")
                error_data = json.dumps({"error": str(e)})
                yield f"data: {json.dumps(error_data)}\n\n"

        return generate

    def invoke_and_save(self, bot_id, user_id, input_text, hide: bool = False) -> str:
        # Save the user question with role "human"
        message_service.save_message(bot_id, user_id, "user", input_text, hide)

        # Get the AI response
        result = self.conversational_rag_chain.invoke(
            {"input": input_text},
            config={"configurable": {"session_id": f"{bot_id}_{user_id}"}},
        )["answer"]

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
            logger.error(f"Failed to load session history for {session_id}: {e}")
        finally:
            db.session.close()
        return chat_history
