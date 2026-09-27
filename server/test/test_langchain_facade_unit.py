"""Unit tests for LangChainFacade (fake chat model and retriever: no
ChromaDB, no LLM) and for RagService on top of a fake facade."""

import asyncio
from types import SimpleNamespace

from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from src.services.langchain_facade import ChatTurn, LangChainFacade
from src.services.rag_svc import RagService

BOT_ID, USER_ID = 10, 1
HISTORY = [ChatTurn("user", "bonjour"), ChatTurn("assistant", "salut")]


class FakeRetriever:
    def __init__(self):
        self.queries = []

    def invoke(self, question):
        self.queries.append(question)
        return [
            Document(page_content="Paris est la capitale.", metadata={"name": "Géo"}),
            Document(page_content="Sans source.", metadata={}),
        ]


class FakeVectorStore:
    def __init__(self):
        self.retriever = FakeRetriever()
        self.collections = []

    def build_retriever(self, collection_name):
        self.collections.append(collection_name)
        return self.retriever


class FakeLlmService:
    def __init__(self, llm):
        self.llm = llm
        self.calls = []

    def get_llm(self, user_id=None, bot_id=None, session_id=None):
        self.calls.append((user_id, bot_id, session_id))
        return self.llm


def _recording_llm(prompts):
    """A chat model stand-in that keeps the prompt it was sent."""

    def respond(prompt_value):
        prompts.append(prompt_value.to_messages())
        return AIMessage(content="Paris.")

    return RunnableLambda(respond)


def test_answer_sends_context_history_and_question_to_the_llm():
    prompts = []
    llm_service = FakeLlmService(_recording_llm(prompts))
    db = FakeVectorStore()
    facade = LangChainFacade(llm_service, db)

    answer = asyncio.run(
        facade.answer(BOT_ID, "Tu es {Alfred}.", "Capitale ?", HISTORY, USER_ID, 7)
    )

    assert answer == "Paris."
    assert db.collections == [f"Collection{BOT_ID}"]
    assert db.retriever.queries == ["Capitale ?"]
    assert llm_service.calls == [(USER_ID, BOT_ID, 7)]
    system, human_1, ai_1, question = prompts[0]
    assert system.type == "system"
    # user braces are escaped, not treated as template variables
    assert system.content.startswith("Tu es {Alfred}.")
    assert "Source: Géo\nParis est la capitale.\n\nSans source." in system.content
    assert [(m.type, m.content) for m in (human_1, ai_1, question)] == [
        ("human", "bonjour"),
        ("ai", "salut"),
        ("human", "Capitale ?"),
    ]


def test_stream_yields_the_answer_chunk_by_chunk():
    llm = GenericFakeChatModel(messages=iter([AIMessage(content="Paris est ici")]))
    facade = LangChainFacade(FakeLlmService(llm), FakeVectorStore())

    async def collect():
        chunks = await facade.stream(BOT_ID, "prompt", "Capitale ?", [], USER_ID)
        return [chunk async for chunk in chunks]

    chunks = asyncio.run(collect())

    assert len(chunks) > 1
    assert "".join(chunks) == "Paris est ici"


class FakeFacade:
    def __init__(self):
        self.histories = []

    async def answer(self, bot_id, bot_prompt, question, history, user_id=None, session_id=None):
        self.histories.append(history)
        return f"réponse à {question}"

    async def stream(self, bot_id, bot_prompt, question, history, user_id=None, session_id=None):
        self.histories.append(history)

        async def chunks():
            yield "réponse "
            yield f"à {question}"

        return chunks()


class FakePromptService:
    async def get_bot_prompt(self, bot_id):
        return "prompt"


class FakeMessageService:
    def __init__(self, stored=()):
        self.stored = list(stored)
        self.saved = []

    async def get_session(self, bot_id, user_id):
        return SimpleNamespace(id=5) if self.stored else None

    async def load_session_history(self, session_id):
        return [SimpleNamespace(role=r, content=c) for r, c in self.stored]

    async def save_message(self, bot_id, user_id, role, content, hide=False):
        self.saved.append((role, content, hide))


def test_rag_ask_reloads_history_then_records_the_new_turn():
    facade = FakeFacade()
    messages = FakeMessageService(stored=[("user", "bonjour"), ("assistant", "salut")])
    rag = RagService(facade, FakePromptService(), messages)

    asyncio.run(rag.ask(BOT_ID, USER_ID, "q1", hide=True))
    asyncio.run(rag.ask(BOT_ID, USER_ID, "q2"))

    assert facade.histories[0] == HISTORY
    assert facade.histories[1] == HISTORY + [
        ChatTurn("user", "q1"),
        ChatTurn("assistant", "réponse à q1"),
    ]
    assert messages.saved == [
        ("user", "q1", True),
        ("assistant", "réponse à q1", False),
        ("user", "q2", False),
        ("assistant", "réponse à q2", False),
    ]


def test_rag_ask_with_stream_emits_sse_and_saves_the_full_answer():
    messages = FakeMessageService()
    rag = RagService(FakeFacade(), FakePromptService(), messages)

    async def run():
        generate = await rag.ask_with_stream(BOT_ID, USER_ID, "{}", "q")
        return [event async for event in generate()]

    events = asyncio.run(run())

    assert events == [
        'data: {"answer": "r\\u00e9ponse "}\n\n',
        'data: {"answer": "\\u00e0 q"}\n\n',
        "data: [DONE]\n\n",
    ]
    assert messages.saved[-1] == ("assistant", "réponse à q", False)
    assert rag.store[f"{BOT_ID}_{USER_ID}"][-1] == ChatTurn("assistant", "réponse à q")
