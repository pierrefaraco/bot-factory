"""Unit tests for ChatFacade against in-memory fake services: no server,
no MySQL, no LLM."""

import asyncio
from types import SimpleNamespace

import pytest

from src.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from src.exceptions.api_error import ApiError
from src.services.chat_facade import ChatFacade

OWNER_ID, GUEST_ID, STRANGER_ID, ADMIN_ID = 1, 2, 3, 4
BOT_ID = 10


class FakeUserAdminService:
    def __init__(self, users):
        self.users = users

    async def get_user_dto_by_id(self, user_id):
        return self.users.get(user_id)


class FakeBotService:
    async def is_bot_belong_to_user(self, bot_id, user_id):
        return bot_id == BOT_ID and user_id == OWNER_ID


class FakeBotAssignmentService:
    async def is_bot_assigned_to_user(self, bot_id, user_id):
        return bot_id == BOT_ID and user_id == GUEST_ID


class FakeBotParametersService:
    async def get_welcome_message(self, user_name, bot_id):
        return f"welcome {user_name}"


class FakeTokenTrackingService:
    def __init__(self, exceeded=False):
        self.exceeded = exceeded

    async def get_token_quota(self, user):
        return {
            "billed_user_id": user.id,
            "limit_24h": 100,
            "used_24h": 100 if self.exceeded else 0,
            "exceeded": self.exceeded,
        }


class FakeMessageService:
    def __init__(self, messages=()):
        self.messages = list(messages)

    async def get_session(self, bot_id, user_id):
        return SimpleNamespace(id=42) if self.messages else None

    async def load_session_history(self, session_id):
        return list(self.messages)

    async def delete_session_history(self, session_id):
        count, self.messages = len(self.messages), []
        return count, 1


class FakeRagService:
    def __init__(self):
        self.calls = []

    async def ask(self, bot_id, user_id, query, hide=False):
        self.calls.append(("ask", bot_id, user_id, query, hide))
        return f"answer to {query}"

    async def ask_with_stream(self, bot_id, user_id, data, query, hide=False, session_id=-1):
        self.calls.append(("stream", bot_id, user_id, query, hide, session_id))

        async def generate():
            yield f"data: {query}\n\n"

        return generate


def _user(user_id, roles, selected_bot_id=BOT_ID):
    return SimpleNamespace(
        id=user_id, roles=roles, name=f"user{user_id}", selected_bot_id=selected_bot_id
    )


def _facade(users=None, exceeded=False, messages=()):
    users = users if users is not None else {
        OWNER_ID: _user(OWNER_ID, USER_ROLE),
        GUEST_ID: _user(GUEST_ID, GUEST_ROLE),
        STRANGER_ID: _user(STRANGER_ID, USER_ROLE),
        ADMIN_ID: _user(ADMIN_ID, ADMIN_ROLE, selected_bot_id=99),
    }
    rag = FakeRagService()
    message = FakeMessageService(messages)
    facade = ChatFacade(
        rag,
        FakeUserAdminService(users),
        FakeBotService(),
        FakeBotAssignmentService(),
        FakeBotParametersService(),
        message,
        FakeTokenTrackingService(exceeded),
    )
    return facade, rag, message


async def _drain(iterator):
    return [chunk async for chunk in iterator]


@pytest.mark.parametrize("user_id", [OWNER_ID, GUEST_ID, ADMIN_ID])
def test_ask_serves_every_role_allowed_on_the_bot(user_id):
    facade, rag, _ = _facade()

    assert asyncio.run(facade.ask(user_id, "hello")) == "answer to hello"
    assert rag.calls[0][:3] == ("ask", 99 if user_id == ADMIN_ID else BOT_ID, user_id)


@pytest.mark.parametrize(
    "users, user_id, status",
    [
        ({}, OWNER_ID, 401),
        ({OWNER_ID: _user(OWNER_ID, USER_ROLE, selected_bot_id=None)}, OWNER_ID, 409),
        (None, STRANGER_ID, 403),
    ],
)
def test_ask_rejects_before_calling_the_llm(users, user_id, status):
    facade, rag, _ = _facade(users=users)

    with pytest.raises(ApiError) as exc:
        asyncio.run(facade.ask(user_id, "hello"))
    assert exc.value.status_code == status
    assert rag.calls == []


def test_ask_rejects_once_the_token_quota_is_exceeded():
    facade, rag, _ = _facade(exceeded=True)

    with pytest.raises(ApiError) as exc:
        asyncio.run(facade.ask(OWNER_ID, "hello"))
    assert exc.value.status_code == 429
    assert rag.calls == []


def test_stream_yields_the_rag_chunks():
    facade, rag, _ = _facade()

    iterator = asyncio.run(facade.stream(OWNER_ID, str(BOT_ID), "hello", "{}"))

    assert asyncio.run(_drain(iterator)) == ["data: hello\n\n"]
    assert rag.calls == [("stream", BOT_ID, OWNER_ID, "hello", False, -1)]


@pytest.mark.parametrize(
    "bot_id, question, data, message",
    [
        (str(BOT_ID), "  ", "{}", "Question parameter is required"),
        (None, "hello", "{}", "Bot_id is required"),
        ("abc", "hello", "{}", "Invalid bot_id format"),
        (str(BOT_ID), "hello", "{not json", "Invalid JSON in data parameter"),
    ],
)
def test_stream_rejects_invalid_parameters(bot_id, question, data, message):
    facade, rag, _ = _facade()

    with pytest.raises(ApiError, match=message) as exc:
        asyncio.run(facade.stream(OWNER_ID, bot_id, question, data))
    assert exc.value.status_code == 400
    assert rag.calls == []


def test_welcome_wipes_history_then_asks_the_hidden_welcome_question():
    facade, rag, message = _facade(messages=["old"])

    assert asyncio.run(facade.welcome(OWNER_ID)) == "answer to welcome user1"
    assert message.messages == []
    assert rag.calls == [("ask", BOT_ID, OWNER_ID, "welcome user1", True)]


def test_stream_welcome_keeps_history_and_passes_the_session_id():
    facade, rag, message = _facade(messages=["old"])

    asyncio.run(_drain(asyncio.run(facade.stream_welcome(OWNER_ID, "{}"))))

    assert message.messages == ["old"]
    assert rag.calls == [("stream", BOT_ID, OWNER_ID, "welcome user1", True, 42)]


def test_history_and_delete_history():
    facade, _, _ = _facade(messages=["a", "b"])

    assert asyncio.run(facade.history(BOT_ID, OWNER_ID)) == ["a", "b"]
    assert asyncio.run(facade.delete_selected_bot_history(OWNER_ID)) == (2, 1)
    assert asyncio.run(facade.history(BOT_ID, OWNER_ID)) == []
    assert asyncio.run(facade.delete_history(BOT_ID, OWNER_ID)) == 0
