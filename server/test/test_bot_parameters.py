"""HTTP regression tests for /api/bot-parameters/* (rest_bot_parameters.py)."""

from ai_server.config.constant import GUEST_ROLE, USER_ROLE
from ai_server.dao.database import BotParameters

from .helpers import assert_error


def test_create_golden_path(
    http_client, api_base_url, create_user, create_bot, login, track
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/bot-parameters",
        json={"bot_id": bot.id, "bot_name": "Test Bot", "interlocutor_identity": "USER"},
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["bot_id"] == bot.id
    track(BotParameters, body["id"])


def test_create_without_interlocutor_identity_defaults_to_user(
    http_client, api_base_url, create_user, create_bot, login, track
):
    # interlocutor_identity is Optional in the request DTO; omitting it
    # should fall back to a valid InterlocutorIdentity default (USER)
    # rather than crashing.
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/bot-parameters",
        json={"bot_id": bot.id, "bot_name": "Test Bot"},
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["interlocutor_identity"] == "USER"
    track(BotParameters, body["id"])


def test_create_missing_content_type(
    http_client, api_base_url, create_user, create_bot, login
):
    # No before_request Content-Type hook on this blueprint: a non-JSON
    # Content-Type reaches spectree's own validation first, which reports
    # missing fields rather than the handler's dead-code is_json check
    # (same situation as rest_users_admin.py's register()).
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/bot-parameters",
        data='{"bot_id": 1}',
        headers={**headers, "Content-Type": "text/plain"},
    )

    assert_error(response, 400, "Field required")


def test_create_requires_auth(http_client, api_base_url, create_user, create_bot):
    user, _password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)

    response = http_client.post(
        f"{api_base_url}/bot-parameters", json={"bot_id": bot.id}
    )

    assert_error(response, 401)


def test_create_forbidden_for_guest(http_client, api_base_url, create_user, login):
    guest, password = create_user(role=GUEST_ROLE)
    headers = login(guest.mail, password)

    response = http_client.post(
        f"{api_base_url}/bot-parameters", json={"bot_id": 1}, headers=headers
    )

    assert_error(response, 403, "Access denied")


def test_patch_golden_path(
    http_client, api_base_url, create_user, create_bot, create_bot_parameters, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_bot_parameters(bot.id)
    headers = login(user.mail, password)

    response = http_client.patch(
        f"{api_base_url}/bot-parameters/{bot.id}",
        json={"goal": "updated goal"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["goal"] == "updated goal"


def test_patch_not_found(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.patch(
        f"{api_base_url}/bot-parameters/{bot.id}", json={"goal": "x"}, headers=headers
    )

    assert_error(response, 404, "not found")


def test_get_golden_path(
    http_client, api_base_url, create_user, create_bot, create_bot_parameters, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_bot_parameters(bot.id)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/bot-parameters/{bot.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["bot_id"] == bot.id


def test_get_not_found(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/bot-parameters/{bot.id}", headers=headers
    )

    assert_error(response, 404, "not found")


def test_delete_golden_path(
    http_client, api_base_url, create_user, create_bot, create_bot_parameters, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_bot_parameters(bot.id)
    headers = login(user.mail, password)

    response = http_client.delete(
        f"{api_base_url}/bot-parameters/{bot.id}", headers=headers
    )

    assert response.status_code == 204, response.text


def test_delete_not_found(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.delete(
        f"{api_base_url}/bot-parameters/{bot.id}", headers=headers
    )

    assert_error(response, 404, "not found")
