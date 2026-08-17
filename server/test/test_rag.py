"""HTTP regression tests for /api/rag/* (rest_rag.py).

Chat/streaming endpoints call the real LLM via langchain_mistralai, which is
redirected to the deterministic mock server (server/test/mock_llm/) via the
MISTRAL_BASE_URL env var on the api container (see
docker-compose.test.yml) -- no real Mistral API key or network call needed.
"""

import json

import pytest

from ai_server.config.constant import ADMIN_ROLE, USER_ROLE
from ai_server.dao.database import Message, Session as SessionModel, TokenUsage

from .helpers import assert_error, read_sse

CANNED_TEXT = "This is a deterministic mock LLM response."


def _select_bot(db_session, user, bot):
    user.selected_bot_id = bot.id
    db_session.commit()


@pytest.fixture()
def track_rag_session(db_session, track):
    """Chat/streaming endpoints create Session/Message rows server-side
    (message_service.save_message/get_session), and a successful LLM call
    also records a TokenUsage row (llm_svc.TokenCountingCallback). None of
    these have an ondelete=CASCADE tying them back to bot or user, so
    without this they'd survive bot/user cleanup and the registry's later
    `DELETE FROM user_account` would fail on their foreign keys."""

    def _track(bot_id, user_id):
        sessions = (
            db_session.query(SessionModel)
            .filter_by(bot_id=bot_id, user_id=user_id)
            .all()
        )
        for session in sessions:
            for message in db_session.query(Message).filter_by(session_id=session.id):
                track(Message, message.id)
            track(SessionModel, session.id)
        for usage in db_session.query(TokenUsage).filter_by(
            bot_id=bot_id, user_id=user_id
        ):
            track(TokenUsage, usage.id)

    return _track


def test_chat_golden_path(
    http_client, api_base_url, create_user, create_bot, create_bot_parameters,
    login, db_session, track_rag_session,
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_bot_parameters(bot.id, interlocutor_identity="USER")
    _select_bot(db_session, user, bot)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/rag/chat", json={"question": "Hello?"}, headers=headers
    )
    # Track before asserting: a 200 response already means the Session/
    # Message/TokenUsage rows exist server-side, so cleanup must happen
    # even if a content assertion below fails (e.g. against a real LLM
    # instead of the mock, under make test-server-http-dev).
    if response.status_code == 200:
        track_rag_session(bot.id, user.id)

    assert response.status_code == 200, response.text
    assert CANNED_TEXT in response.json()["response"]


def test_chat_no_bot_selected(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/rag/chat", json={"question": "Hello?"}, headers=headers
    )

    assert_error(response, 409, "select a bot")


def test_chat_forbidden_not_owner(
    http_client, api_base_url, create_user, create_bot, login, db_session
):
    owner, _owner_password = create_user(role=USER_ROLE)
    bot = create_bot(owner.id)
    stranger, stranger_password = create_user(role=USER_ROLE)
    _select_bot(db_session, stranger, bot)
    headers = login(stranger.mail, stranger_password)

    response = http_client.post(
        f"{api_base_url}/rag/chat", json={"question": "Hello?"}, headers=headers
    )

    assert_error(response, 403, "permission")


def test_chat_missing_content_type(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.post(f"{api_base_url}/rag/chat", headers=headers)

    assert_error(response, 400, "Field required")


def test_chat_requires_auth(http_client, api_base_url):
    response = http_client.post(f"{api_base_url}/rag/chat", json={"question": "Hi"})

    assert_error(response, 401)


def test_get_session_history_empty(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/rag/{bot.id}", headers=headers)

    assert response.status_code == 204, response.text


def test_delete_session_history_by_bot_id_empty(
    http_client, api_base_url, create_user, create_bot, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.delete(f"{api_base_url}/rag/{bot.id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json() == {"deleted_message_count": 0}


def test_delete_selected_bot_session_history_no_bot_selected(
    http_client, api_base_url, create_user, login
):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.delete(f"{api_base_url}/rag", headers=headers)

    assert_error(response, 400, "Bot_id is required")


def test_streamchat_golden_path(
    http_client, api_base_url, create_user, create_bot, create_bot_parameters,
    login, track_rag_session,
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_bot_parameters(bot.id, interlocutor_identity="USER")
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/rag/streamchat",
        params={"question": "Hello?", "bot_id": bot.id, "data": "{}"},
        headers=headers,
        stream=True,
    )
    # ask_with_stream() saves the user Message/Session synchronously before
    # returning the generator, so this is safe to track before reading the
    # stream body or asserting on its content.
    if response.status_code == 200:
        track_rag_session(bot.id, user.id)

    assert response.status_code == 200, response.text
    assert response.headers["Content-Type"].startswith("text/event-stream")
    text = read_sse(response)
    assert CANNED_TEXT in text


def test_streamchat_missing_question(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/rag/streamchat",
        params={"bot_id": bot.id},
        headers=headers,
    )

    assert_error(response, 400)


def test_streamchat_forbidden_not_owner(
    http_client, api_base_url, create_user, create_bot, login
):
    owner, _owner_password = create_user(role=USER_ROLE)
    bot = create_bot(owner.id)
    stranger, stranger_password = create_user(role=USER_ROLE)
    headers = login(stranger.mail, stranger_password)

    response = http_client.get(
        f"{api_base_url}/rag/streamchat",
        params={"question": "Hi", "bot_id": bot.id},
        headers=headers,
    )

    assert_error(response, 403, "permission")


def test_trigfirstmessage_non_streaming(
    http_client, api_base_url, create_user, create_bot, create_bot_parameters,
    login, db_session, track_rag_session,
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_bot_parameters(bot.id, interlocutor_identity="USER")
    _select_bot(db_session, user, bot)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/rag/trigfirstmessage",
        params={"stream": "FALSE"},
        headers=headers,
    )
    if response.status_code == 200:
        track_rag_session(bot.id, user.id)

    assert response.status_code == 200, response.text
    assert "response" in response.json()


def test_trigfirstmessage_streaming(
    http_client, api_base_url, create_user, create_bot, create_bot_parameters,
    login, db_session, track_rag_session,
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_bot_parameters(bot.id, interlocutor_identity="USER")
    _select_bot(db_session, user, bot)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/rag/trigfirstmessage",
        params={"stream": "TRUE"},
        headers=headers,
        stream=True,
    )
    if response.status_code == 200:
        track_rag_session(bot.id, user.id)

    assert response.status_code == 200, response.text
    assert response.headers["Content-Type"].startswith("text/event-stream")
    read_sse(response)


def test_trigfirstmessage_no_bot_selected(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/rag/trigfirstmessage", headers=headers)

    assert_error(response, 400, "Bot_id is required")


def test_transmit_to_alfred_golden_path(
    http_client, api_base_url, create_user, create_bot, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/rag/transmit_to_alfred/{bot.id}", json={}, headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Chapters transmitted to Alfred successfully"
