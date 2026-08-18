"""HTTP regression tests for /api/token-stats/* (rest_token_stats.py)."""

from ai_server.config.constant import ADMIN_ROLE, USER_ROLE

from .helpers import assert_error


def test_get_self_golden_path(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_token_usage(user.id, bot.id, total_tokens=42)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/token-stats/me", headers=headers)

    assert response.status_code == 200, response.text


def test_get_self_requires_auth(http_client, api_base_url):
    response = http_client.get(f"{api_base_url}/token-stats/me")

    assert_error(response, 401)


def test_get_guest_golden_path(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role="Guest", parent_id=parent.id)
    bot = create_bot(parent.id)
    create_token_usage(guest.id, bot.id, total_tokens=5)
    headers = login(parent.mail, parent_password)

    response = http_client.get(
        f"{api_base_url}/token-stats/user/{guest.id}", headers=headers
    )

    assert response.status_code == 200, response.text


def test_get_guest_not_owned(http_client, api_base_url, create_user, login):
    stranger, stranger_password = create_user(role=USER_ROLE)
    other_parent, _other_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role="Guest", parent_id=other_parent.id)
    headers = login(stranger.mail, stranger_password)

    response = http_client.get(
        f"{api_base_url}/token-stats/user/{guest.id}", headers=headers
    )

    assert_error(response, 403, "not your guest")


def test_get_guest_not_found(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/token-stats/user/999999999", headers=headers
    )

    assert_error(response, 404, "not found")


def test_get_user_golden_path_admin(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user(role=USER_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(
        f"{api_base_url}/token-stats/user/{target.id}", headers=headers
    )

    assert response.status_code == 200, response.text


def test_get_user_forbidden_for_unrelated_user(
    http_client, api_base_url, create_user, login
):
    user, password = create_user(role=USER_ROLE)
    target, _target_password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/token-stats/user/{target.id}", headers=headers
    )

    assert_error(response, 403, "not your guest")


def test_get_history_self_golden_path(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_token_usage(user.id, bot.id)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/token-stats/history/me", headers=headers
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json()["history"], list)


def test_get_history_self_invalid_limit(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    # spectree's own TokenHistoryQuery(ge=1) validation intercepts before
    # the handler's own manual `if limit < 1...` check is ever reached.
    response = http_client.get(
        f"{api_base_url}/token-stats/history/me",
        params={"limit": 0},
        headers=headers,
    )

    assert_error(response, 400, "greater than or equal to 1")


def test_get_history_guest_golden_path(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role="Guest", parent_id=parent.id)
    bot = create_bot(parent.id)
    create_token_usage(guest.id, bot.id)
    headers = login(parent.mail, parent_password)

    response = http_client.get(
        f"{api_base_url}/token-stats/history/user/{guest.id}", headers=headers
    )

    assert response.status_code == 200, response.text


def test_get_history_user_golden_path_admin(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user(role=USER_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(
        f"{api_base_url}/token-stats/history/user/{target.id}", headers=headers
    )

    assert response.status_code == 200, response.text


def test_get_bot_stats_golden_path(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_token_usage(user.id, bot.id)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/token-stats/bot/{bot.id}", headers=headers)

    assert response.status_code == 200, response.text


def test_get_all_users_golden_path_admin(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(f"{api_base_url}/token-stats/all-users", headers=headers)

    assert response.status_code == 200, response.text
    assert isinstance(response.json()["users"], list)


def test_get_all_users_forbidden_for_non_admin(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/token-stats/all-users", headers=headers)

    assert_error(response, 403, "Access denied")


def test_get_total_self_golden_path(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_token_usage(user.id, bot.id, total_tokens=17)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/token-stats/total/me", headers=headers)

    assert response.status_code == 200, response.text
    # get_user_total_tokens() is typed -> int, but SUM() returns a Decimal
    # and Flask's JSON encoder serializes Decimal as a string, so the wire
    # value is actually a numeric string, not a JSON number -- worth
    # matching exactly (not just semantically) when validating a FastAPI
    # rewrite, since a naive `total_tokens: int` response model there would
    # silently change the wire type.
    assert int(response.json()["total_tokens"]) >= 17


def test_get_total_guest_golden_path(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role="Guest", parent_id=parent.id)
    bot = create_bot(parent.id)
    create_token_usage(guest.id, bot.id, total_tokens=3)
    headers = login(parent.mail, parent_password)

    response = http_client.get(
        f"{api_base_url}/token-stats/total/user/{guest.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["user_id"] == guest.id


def test_get_total_user_golden_path_admin(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user(role=USER_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(
        f"{api_base_url}/token-stats/total/user/{target.id}", headers=headers
    )

    assert response.status_code == 200, response.text


def test_get_last_24h_self_golden_path(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/token-stats/last-24h/me", headers=headers)

    assert response.status_code == 200, response.text
    assert "total_tokens_last_24h" in response.json()


def test_get_last_24h_guest_not_owned(http_client, api_base_url, create_user, login):
    stranger, stranger_password = create_user(role=USER_ROLE)
    other_parent, _other_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role="Guest", parent_id=other_parent.id)
    headers = login(stranger.mail, stranger_password)

    response = http_client.get(
        f"{api_base_url}/token-stats/last-24h/user/{guest.id}", headers=headers
    )

    assert_error(response, 403, "not your guest")


def test_get_last_24h_user_golden_path_admin(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user(role=USER_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(
        f"{api_base_url}/token-stats/last-24h/user/{target.id}", headers=headers
    )

    assert response.status_code == 200, response.text


def test_get_stats_24h_self_golden_path(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/token-stats/stats-24h/me", headers=headers)

    assert response.status_code == 200, response.text


def test_get_stats_24h_guest_golden_path(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role="Guest", parent_id=parent.id)
    bot = create_bot(parent.id)
    create_token_usage(guest.id, bot.id)
    headers = login(parent.mail, parent_password)

    response = http_client.get(
        f"{api_base_url}/token-stats/stats-24h/user/{guest.id}", headers=headers
    )

    assert response.status_code == 200, response.text


def test_get_stats_24h_user_golden_path_admin(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user(role=USER_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(
        f"{api_base_url}/token-stats/stats-24h/user/{target.id}", headers=headers
    )

    assert response.status_code == 200, response.text
