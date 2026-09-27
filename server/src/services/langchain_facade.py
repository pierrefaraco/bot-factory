"""Facade over LangChain for answering a question.

Everything LangChain-specific about a question/answer turn lives here and
nowhere else: the LCEL chain (`|`), the ChatPromptTemplate, the Chroma
retriever, the chat model, and LangChain's message types. Callers
(RagService) only see plain Python: a bot prompt and a question in, the
chat history as a list of ChatTurn, and a str -- or an async iterator of
str chunks -- out. Swapping LangChain for another library means rewriting
this module, not its callers.

Its subsystems are LlmService (the token-tracked chat model) and
VectorStoreFacade (the per-bot vector store). Document ingestion is not
covered: KnowledgeSvc drives VectorStoreFacade directly for that.
"""

from dataclasses import dataclass
from typing import AsyncIterator

import langchain
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from starlette.concurrency import run_in_threadpool

from src.log.bot_factory_logger import BotFactoryLogger
from src.log.prompt_debug_logger import PromptDebugLogger
from src.services.vector_store_facade import VectorStoreFacade
from src.services.llm_svc import LlmService

langchain.debug = False

# ===== LOGGERS INIT =====
logger = BotFactoryLogger()
prompt_debug_logger = PromptDebugLogger()


@dataclass(frozen=True)
class ChatTurn:
    """One message of a conversation, library-agnostic. `role` is
    "assistant" for the bot, anything else ("user") for the human --
    the same convention as MessageDto.role."""

    role: str
    content: str


class LangChainFacade:

    def __init__(self, llm_service: LlmService, vector_store: VectorStoreFacade):
        self.llm_service = llm_service
        self.vector_store = vector_store

    # ===== PUBLIC API =====

    async def answer(
        self,
        bot_id: int,
        bot_prompt: str,
        question: str,
        history: list[ChatTurn],
        user_id=None,
        session_id=None,
    ) -> str:
        """Run the RAG pipeline once and return the whole answer."""
        chain = await self._build_chain(bot_id, bot_prompt, user_id, session_id)
        answer = await chain.ainvoke(self._inputs(question, history))
        self._log_llm_answer(answer)
        return answer

    async def stream(
        self,
        bot_id: int,
        bot_prompt: str,
        question: str,
        history: list[ChatTurn],
        user_id=None,
        session_id=None,
    ) -> AsyncIterator[str]:
        """Run the RAG pipeline and return the answer as it is generated,
        one text chunk at a time.

        A coroutine returning the iterator rather than an async generator
        itself: the chain is built (retriever, model) as soon as this is
        awaited, so a failure there reaches the caller before any SSE
        response has started, instead of surfacing mid-stream."""
        chain = await self._build_chain(bot_id, bot_prompt, user_id, session_id)
        return self._stream_chunks(chain, self._inputs(question, history))

    # ===== CHAIN CONSTRUCTION =====

    async def _build_chain(
        self, bot_id, bot_prompt: str, user_id, session_id
    ) -> Runnable:
        # build() is run via run_in_threadpool: it's genuinely blocking
        # under the hood (ChromaDB client init in
        # vector_store.build_retriever()), with no async equivalent -- see
        # build()'s own docstring.
        return await run_in_threadpool(
            self.build, bot_id, bot_prompt, user_id, session_id
        )

    def build(self, bot_id, bot_prompt: str, user_id=None, session_id=None) -> Runnable:
        """Assemble a fresh single-call RAG pipeline for one question, as a
        plain LCEL chain (no create_history_aware_retriever /
        create_retrieval_chain / RunnableWithMessageHistory indirection).

        Rebuilt on every call rather than cached on `self`: each call needs
        its own TokenCountingCallback (tied to this user_id/bot_id/session_id)
        and the app-wide LangChainFacade is shared across concurrent
        requests, so the built chain is returned instead of stored as
        instance state.

        Genuinely blocking under the hood, with no async equivalent:
        vector_store.build_retriever() (a real ChromaDB client init). Hence
        _build_chain() runs this via run_in_threadpool so it doesn't block
        the event loop.

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
        log happens in answer()/_stream_chunks() instead, once the full
        answer is already accumulated — same debug value, no chain step in
        the way.
        """
        llm = self.llm_service.get_llm(
            user_id=user_id, bot_id=bot_id, session_id=session_id
        )
        retriever = self.vector_store.build_retriever(f"Collection{bot_id}")
        qa_prompt = self._qa_prompt(bot_id, bot_prompt)

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

    def _qa_prompt(self, bot_id, prompt: str) -> ChatPromptTemplate:
        # The stored prompt contains user-provided text (bot name, goal, ...):
        # escape braces so LangChain does not treat them as template variables.
        escaped_prompt = prompt.replace("{", "{{").replace("}", "}}")
        bot_prompt = f"{escaped_prompt}\n\n<context>\n{{context}}\n</context>"
        logger.debug(f"QA prompt created for bot_id {bot_id}")
        return ChatPromptTemplate.from_messages(
            [
                ("system", bot_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

    def _inputs(self, question: str, history: list[ChatTurn]) -> dict:
        return {
            "input": question,
            "chat_history": [self._to_message(turn) for turn in history],
        }

    def _to_message(self, turn: ChatTurn) -> BaseMessage:
        if turn.role == "assistant":
            return AIMessage(content=turn.content)
        return HumanMessage(content=turn.content)

    async def _stream_chunks(self, chain: Runnable, inputs: dict) -> AsyncIterator[str]:
        answer = ""
        async for chunk in chain.astream(inputs):
            if chunk:
                answer += chunk
                yield chunk
        self._log_llm_answer(answer)

    # ===== CHAIN STEPS =====

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

    def _retrieve_and_label_sources(self, retriever, question: str):
        """Fetch matching chunks for the raw question, then label each one
        with its source knowledge chapter (see _label_documents_with_source)."""
        return self._label_documents_with_source(retriever.invoke(question))

    def _format_docs(self, docs) -> str:
        """Stuff the labeled documents into a single string for the
        {context} slot of the bot's system prompt."""
        return "\n\n".join(doc.page_content for doc in docs)

    # ===== PROMPT DEBUG LOGGING =====

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
        logged after the chain so it can't block `.stream()`."""
        prompt_debug_logger.debug(f"④ raw LLM answer: {self._truncate(answer)}")
