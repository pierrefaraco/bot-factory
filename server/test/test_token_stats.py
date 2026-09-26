"""HTTP regression tests for /api/token-stats/* (rest_token_stats.py)."""

from datetime import datetime, timedelta, timezone

import pytest

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


def test_get_history_self_only_returns_own_usage(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    user, password = create_user(role=USER_ROLE)
    other, _other_password = create_user(role=USER_ROLE)
    own = create_token_usage(user.id, create_bot(user.id).id)
    create_token_usage(other.id, create_bot(other.id).id)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/token-stats/history/me", headers=headers
    )

    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()["history"]] == [own.id]


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


def test_get_admin_summary_requires_auth(http_client, api_base_url):
    response = http_client.get(f"{api_base_url}/token-stats/admin-summary")

    assert_error(response, 401)


def test_get_admin_summary_rolls_up_guest_usage_under_parent(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    # A guest's usage is always recorded under its parent's user_id with
    # user_guest_id set to the guest's own id (see TokenCountingCallback.
    # on_llm_end in llm_svc.py) -- the account total must include it, and
    # the guest must also show up separately keyed by its own id.
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role="Guest", parent_id=parent.id)
    bot = create_bot(parent.id)
    create_token_usage(parent.id, bot.id, user_guest_id=guest.id, total_tokens=42)
    headers = login(parent.mail, parent_password)

    response = http_client.get(f"{api_base_url}/token-stats/admin-summary", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["accounts"][str(parent.id)]["tokens_24h"] == 42
    assert body["accounts"][str(parent.id)]["tokens_30d"] == 42
    assert body["guests"][str(guest.id)]["tokens_24h"] == 42
    assert body["guests"][str(guest.id)]["tokens_30d"] == 42


def test_get_admin_summary_scopes_to_own_account_for_user_role(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    caller, caller_password = create_user(role=USER_ROLE)
    caller_bot = create_bot(caller.id)
    create_token_usage(caller.id, caller_bot.id, total_tokens=10)

    stranger, _stranger_password = create_user(role=USER_ROLE)
    stranger_bot = create_bot(stranger.id)
    create_token_usage(stranger.id, stranger_bot.id, total_tokens=99)

    headers = login(caller.mail, caller_password)

    response = http_client.get(f"{api_base_url}/token-stats/admin-summary", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert str(caller.id) in body["accounts"]
    assert str(stranger.id) not in body["accounts"]


def test_get_admin_summary_sees_everyone_for_admin(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    other, _other_password = create_user(role=USER_ROLE)
    other_bot = create_bot(other.id)
    create_token_usage(other.id, other_bot.id, total_tokens=7)

    headers = login(admin.mail, admin_password)

    response = http_client.get(f"{api_base_url}/token-stats/admin-summary", headers=headers)

    assert response.status_code == 200, response.text
    assert str(other.id) in response.json()["accounts"]


def test_get_admin_summary_excludes_usage_older_than_30d(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login, db_session
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    old_usage = create_token_usage(user.id, bot.id, total_tokens=15)
    old_usage.timestamp = datetime.now(timezone.utc) - timedelta(days=31)
    db_session.commit()
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/token-stats/admin-summary", headers=headers)

    assert response.status_code == 200, response.text
    assert str(user.id) not in response.json()["accounts"]


def test_get_admin_summary_splits_24h_from_30d(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login, db_session
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_token_usage(user.id, bot.id, total_tokens=5)  # within last 24h
    older_usage = create_token_usage(user.id, bot.id, total_tokens=20)
    older_usage.timestamp = datetime.now(timezone.utc) - timedelta(days=5)
    db_session.commit()
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/token-stats/admin-summary", headers=headers)

    assert response.status_code == 200, response.text
    account = response.json()["accounts"][str(user.id)]
    assert account["tokens_24h"] == 5
    assert account["tokens_30d"] == 25


def test_quota_self_golden_path(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_token_usage(user.id, bot.id, total_tokens=42)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/token-stats/quota/me", headers=headers)

    assert response.status_code == 200, response.text
    quota = response.json()
    assert quota["billed_user_id"] == user.id
    assert quota["used_24h"] == 42


def test_quota_guest_billed_to_parent(
    http_client, api_base_url, create_user, create_bot, create_token_usage, login
):
    parent, _parent_password = create_user(role=USER_ROLE)
    guest, guest_password = create_user(role="Guest", parent_id=parent.id)
    bot = create_bot(parent.id)
    create_token_usage(parent.id, bot.id, user_guest_id=guest.id, total_tokens=7)
    headers = login(guest.mail, guest_password)

    response = http_client.get(f"{api_base_url}/token-stats/quota/me", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["billed_user_id"] == parent.id
    assert response.json()["used_24h"] == 7


def test_chat_rejected_when_token_limit_reached(
    http_client, api_base_url, create_user, create_bot, create_bot_parameters,
    create_token_usage, login, db_session,
):
    user, password = create_user(role=USER_ROLE)
    bot = create_bot(user.id)
    create_bot_parameters(bot.id, interlocutor_identity="USER")
    user.selected_bot_id = bot.id
    db_session.commit()
    headers = login(user.mail, password)

    limit = http_client.get(
        f"{api_base_url}/token-stats/quota/me", headers=headers
    ).json()["limit_24h"]
    if limit is None:
        pytest.skip("TOKEN_LIMIT_PER_USER_24H is disabled on the API under test")
    create_token_usage(user.id, bot.id, total_tokens=limit)

    response = http_client.post(
        f"{api_base_url}/rag/chat", json={"question": "Hello?"}, headers=headers
    )

    assert_error(response, 429, "Token limit reached")
