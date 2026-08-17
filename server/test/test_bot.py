"""HTTP regression tests for /api/bot/* (rest_bot.py).

Bots created via POST /bot also insert BotAvatar/BotParameters/Knowledge
rows (bot_svc.create_random_bot -> avatar/parameters/template import), but
all three have ondelete=CASCADE to bot.id, so tracking just the Bot row for
cleanup is enough.
"""

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dao.database import Bot, User

from .helpers import assert_error


def test_create_bot_golden_path(http_client, api_base_url, create_user, login, track):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.post(f"{api_base_url}/bot", json={}, headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user_account_id"] == user.id
    track(Bot, body["id"])


def test_create_bot_missing_content_type(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.post(f"{api_base_url}/bot", headers=headers)

    assert_error(response, 400, "Content-Type")


def test_create_bot_requires_auth(http_client, api_base_url):
    response = http_client.post(f"{api_base_url}/bot", json={})

    assert_error(response, 401)


def test_create_bot_forbidden_for_guest(http_client, api_base_url, create_user, login):
    guest, password = create_user(role=GUEST_ROLE)
    headers = login(guest.mail, password)

    response = http_client.post(f"{api_base_url}/bot", json={}, headers=headers)

    assert_error(response, 403, "Access denied")


def test_get_bot_golden_path(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/bot/{bot.id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["id"] == bot.id


def test_get_bot_not_owner(http_client, api_base_url, create_user, create_bot, login):
    owner, _owner_password = create_user(role=USER_ROLE)
    bot = create_bot(owner.id)
    stranger, stranger_password = create_user(role=USER_ROLE)
    headers = login(stranger.mail, stranger_password)

    response = http_client.get(f"{api_base_url}/bot/{bot.id}", headers=headers)

    assert_error(response, 403)


def test_get_bot_not_found(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/bot/999999999", headers=headers)

    assert_error(response, 404, "Bot not found")


def test_get_bot_requires_auth(http_client, api_base_url, create_user, create_bot):
    user, _password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)

    response = http_client.get(f"{api_base_url}/bot/{bot.id}")

    assert_error(response, 401)


def test_get_self_bots_golden_path(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/bot/self", headers=headers)

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_get_all_bots_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(f"{api_base_url}/bot", headers=headers)

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_get_all_bots_forbidden_for_guest(http_client, api_base_url, create_user, login):
    guest, password = create_user(role=GUEST_ROLE)
    headers = login(guest.mail, password)

    response = http_client.get(f"{api_base_url}/bot", headers=headers)

    assert_error(response, 403, "Access denied")


def test_get_owned_bots_golden_path(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/bot/owned", headers=headers)

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_update_bot_golden_path(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.put(
        f"{api_base_url}/bot/{bot.id}", json={"description": "updated"}, headers=headers
    )

    assert response.status_code == 200, response.text


def test_update_bot_not_owner(http_client, api_base_url, create_user, create_bot, login):
    owner, _owner_password = create_user(role=USER_ROLE)
    bot = create_bot(owner.id)
    stranger, stranger_password = create_user(role=USER_ROLE)
    headers = login(stranger.mail, stranger_password)

    response = http_client.put(
        f"{api_base_url}/bot/{bot.id}", json={"description": "x"}, headers=headers
    )

    assert_error(response, 403)


def test_update_bot_not_found(http_client, api_base_url, create_user, login):
    # _can_modify_bot() can't verify ownership of a bot that doesn't exist,
    # so this surfaces as 403 rather than 404.
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.put(
        f"{api_base_url}/bot/999999999", json={"description": "x"}, headers=headers
    )

    assert_error(response, 403)


def test_update_bot_missing_content_type(
    http_client, api_base_url, create_user, create_bot, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.put(f"{api_base_url}/bot/{bot.id}", headers=headers)

    assert_error(response, 400, "Content-Type")


def test_delete_bot_golden_path(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.delete(f"{api_base_url}/bot/{bot.id}", headers=headers)

    assert response.status_code == 204, response.text


def test_delete_bot_not_owner(http_client, api_base_url, create_user, create_bot, login):
    owner, _owner_password = create_user(role=USER_ROLE)
    bot = create_bot(owner.id)
    stranger, stranger_password = create_user(role=USER_ROLE)
    headers = login(stranger.mail, stranger_password)

    response = http_client.delete(f"{api_base_url}/bot/{bot.id}", headers=headers)

    assert_error(response, 403)


def test_delete_bot_not_found(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.delete(f"{api_base_url}/bot/999999999", headers=headers)

    assert_error(response, 403)


def test_get_bot_parameters_description_golden_path(
    http_client, api_base_url, create_user, login
):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/bot/parameters-description", headers=headers
    )

    assert response.status_code == 200, response.text


def test_select_bot_golden_path(
    http_client, api_base_url, create_user, create_bot, login, db_session
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.patch(
        f"{api_base_url}/bot/selectbot/{bot.id}", headers=headers
    )

    assert response.status_code == 204, response.text
    db_session.expire_all()
    refreshed = db_session.get(User, user.id)
    assert refreshed.selected_bot_id == bot.id
