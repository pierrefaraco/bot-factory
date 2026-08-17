"""HTTP regression tests for /api/avatar/* (rest_avatar.py)."""

from ai_server.config.constant import GUEST_ROLE, USER_ROLE
from ai_server.dao.database import BotAvatar

from .helpers import assert_error


def test_create_random_golden_path(
    http_client, api_base_url, create_user, create_bot, login, track
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/avatar/random", json={"bot_id": bot.id}, headers=headers
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["bot_id"] == bot.id
    track(BotAvatar, body["id"])


def test_create_random_missing_content_type(
    http_client, api_base_url, create_user, create_bot, login
):
    # No before_request Content-Type hook on this blueprint either: a
    # non-JSON Content-Type reaches spectree's own validation first (same
    # situation as rest_bot_parameters.py).
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/avatar/random",
        data='{"bot_id": 1}',
        headers={**headers, "Content-Type": "text/plain"},
    )

    assert_error(response, 400, "Field required")


def test_create_random_requires_auth(http_client, api_base_url, create_user, create_bot):
    user, _password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)

    response = http_client.post(f"{api_base_url}/avatar/random", json={"bot_id": bot.id})

    assert_error(response, 401)


def test_create_random_forbidden_for_guest(http_client, api_base_url, create_user, login):
    guest, password = create_user(role=GUEST_ROLE)
    headers = login(guest.mail, password)

    response = http_client.post(
        f"{api_base_url}/avatar/random", json={"bot_id": 1}, headers=headers
    )

    assert_error(response, 403, "Access denied")


def test_create_golden_path(
    http_client, api_base_url, create_user, create_bot, login, track
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.post(
        f"{api_base_url}/avatar",
        json={"bot_id": bot.id, "body": 1, "hat": 2, "eyes": 3, "mouth": 4},
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["bot_id"] == bot.id
    track(BotAvatar, body["id"])


def test_update_golden_path(
    http_client, api_base_url, create_user, create_bot, create_avatar, login
):
    # PUT/PATCH key off the avatar row's own id, not bot_id (both DTOs
    # declare id as a field for this reason).
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    avatar = create_avatar(bot.id)
    headers = login(user.mail, password)

    response = http_client.put(
        f"{api_base_url}/avatar",
        json={"id": avatar.id, "bot_id": bot.id, "hat": 9},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["hat"] == 9


def test_patch_golden_path(
    http_client, api_base_url, create_user, create_bot, create_avatar, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    avatar = create_avatar(bot.id)
    headers = login(user.mail, password)

    response = http_client.patch(
        f"{api_base_url}/avatar", json={"id": avatar.id, "hat": 7}, headers=headers
    )

    assert response.status_code == 204, response.text


def test_patch_missing_content_type(
    http_client, api_base_url, create_user, create_bot, create_avatar, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_avatar(bot.id)
    headers = login(user.mail, password)

    response = http_client.patch(f"{api_base_url}/avatar", headers=headers)

    assert_error(response, 400, "Content-Type")


def test_get_golden_path(
    http_client, api_base_url, create_user, create_bot, create_avatar, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_avatar(bot.id)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/avatar/{bot.id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["bot_id"] == bot.id


def test_get_not_found(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/avatar/{bot.id}", headers=headers)

    assert_error(response, 404, "not found")


def test_delete_golden_path(
    http_client, api_base_url, create_user, create_bot, create_avatar, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_avatar(bot.id)
    headers = login(user.mail, password)

    response = http_client.delete(f"{api_base_url}/avatar/{bot.id}", headers=headers)

    assert response.status_code == 204, response.text


def test_delete_not_found(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.delete(f"{api_base_url}/avatar/{bot.id}", headers=headers)

    assert_error(response, 404, "not found")
