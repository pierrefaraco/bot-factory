"""HTTP regression tests for /api/bot-guest-assignment/* (rest_bot_assignment.py)."""

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dao.database import BotAssignment

from .helpers import assert_error


def test_create_golden_path(
    http_client, api_base_url, create_user, create_bot, login, track
):
    parent, parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.post(
        f"{api_base_url}/bot-guest-assignment",
        json={"bot_id": bot.id, "guest_user_id": guest.id},
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["bot_id"] == bot.id
    assert body["user_id"] == guest.id
    track(BotAssignment, body["id"])


def test_create_missing_content_type(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.post(f"{api_base_url}/bot-guest-assignment", headers=headers)

    assert_error(response, 400, "Field required")


def test_create_forbidden_for_guest(http_client, api_base_url, create_user, login):
    guest, password = create_user(role=GUEST_ROLE)
    headers = login(guest.mail, password)

    response = http_client.post(
        f"{api_base_url}/bot-guest-assignment",
        json={"bot_id": 1, "guest_user_id": 1},
        headers=headers,
    )

    assert_error(response, 403, "Access denied")


def test_get_by_parent_golden_path_self(
    http_client, api_base_url, create_user, create_bot, create_bot_assignment, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    create_bot_assignment(bot.id, guest.id, parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.get(
        f"{api_base_url}/bot-guest-assignment/parent/{parent.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_get_by_parent_golden_path_as_admin(
    http_client, api_base_url, create_user, create_bot, create_bot_assignment, login
):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    parent, _parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    create_bot_assignment(bot.id, guest.id, parent.id)
    headers = login(admin.mail, admin_password)

    response = http_client.get(
        f"{api_base_url}/bot-guest-assignment/parent/{parent.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_get_by_parent_forbidden_for_other_user(
    http_client, api_base_url, create_user, login
):
    parent, _parent_password = create_user(role=USER_ROLE)
    stranger, stranger_password = create_user(role=USER_ROLE)
    headers = login(stranger.mail, stranger_password)

    response = http_client.get(
        f"{api_base_url}/bot-guest-assignment/parent/{parent.id}", headers=headers
    )

    assert_error(response, 403, "Forbidden")


def test_get_by_guest_golden_path(
    http_client, api_base_url, create_user, create_bot, create_bot_assignment, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    create_bot_assignment(bot.id, guest.id, parent.id)
    headers = login(guest.mail, guest_password)

    response = http_client.get(
        f"{api_base_url}/bot-guest-assignment/guest/{guest.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_get_by_guest_forbidden_for_other_guest(
    http_client, api_base_url, create_user, login
):
    guest, _guest_password = create_user(role=GUEST_ROLE)
    other_guest, other_password = create_user(role=GUEST_ROLE)
    headers = login(other_guest.mail, other_password)

    response = http_client.get(
        f"{api_base_url}/bot-guest-assignment/guest/{guest.id}", headers=headers
    )

    assert_error(response, 403, "Forbidden")


def test_get_assigned_bot_ids_golden_path(
    http_client, api_base_url, create_user, create_bot, create_bot_assignment, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    create_bot_assignment(bot.id, guest.id, parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.get(
        f"{api_base_url}/bot-guest-assignment/guest/{guest.id}/bot-ids", headers=headers
    )

    assert response.status_code == 200, response.text
    assert bot.id in response.json()["bot_ids"]


def test_update_golden_path_self(
    http_client, api_base_url, create_user, create_bot, create_bot_assignment, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    assignment = create_bot_assignment(bot.id, guest.id, parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.put(
        f"{api_base_url}/bot-guest-assignment/{assignment.id}",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


def test_update_golden_path_as_admin(
    http_client, api_base_url, create_user, create_bot, create_bot_assignment, login
):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    parent, _parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    assignment = create_bot_assignment(bot.id, guest.id, parent.id)
    headers = login(admin.mail, admin_password)

    response = http_client.put(
        f"{api_base_url}/bot-guest-assignment/{assignment.id}",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


def test_update_forbidden_for_non_owner(
    http_client, api_base_url, create_user, create_bot, create_bot_assignment, login
):
    parent, _parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    assignment = create_bot_assignment(bot.id, guest.id, parent.id)
    stranger, stranger_password = create_user(role=USER_ROLE)
    headers = login(stranger.mail, stranger_password)

    response = http_client.put(
        f"{api_base_url}/bot-guest-assignment/{assignment.id}",
        json={"is_active": False},
        headers=headers,
    )

    assert_error(response, 403, "Forbidden")


def test_update_not_found(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.put(
        f"{api_base_url}/bot-guest-assignment/999999999",
        json={"is_active": False},
        headers=headers,
    )

    assert_error(response, 404, "not found")


def test_delete_golden_path_self(
    http_client, api_base_url, create_user, create_bot, create_bot_assignment, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    assignment = create_bot_assignment(bot.id, guest.id, parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.delete(
        f"{api_base_url}/bot-guest-assignment/{assignment.id}", headers=headers
    )

    assert response.status_code == 204, response.text


def test_delete_golden_path_as_admin(
    http_client, api_base_url, create_user, create_bot, create_bot_assignment, login
):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    parent, _parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    assignment = create_bot_assignment(bot.id, guest.id, parent.id)
    headers = login(admin.mail, admin_password)

    response = http_client.delete(
        f"{api_base_url}/bot-guest-assignment/{assignment.id}", headers=headers
    )

    assert response.status_code == 204, response.text


def test_delete_not_found(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.delete(
        f"{api_base_url}/bot-guest-assignment/999999999", headers=headers
    )

    assert_error(response, 404, "not found")


def test_remove_golden_path(
    http_client, api_base_url, create_user, create_bot, create_bot_assignment, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    create_bot_assignment(bot.id, guest.id, parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.request(
        "DELETE",
        f"{api_base_url}/bot-guest-assignment/remove",
        json={"bot_id": bot.id, "guest_user_id": guest.id},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"message": "Assignment removed successfully"}


def test_remove_missing_fields(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.request(
        "DELETE",
        f"{api_base_url}/bot-guest-assignment/remove",
        json={"bot_id": 1},
        headers=headers,
    )

    assert_error(response, 400)


def test_remove_not_found(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.request(
        "DELETE",
        f"{api_base_url}/bot-guest-assignment/remove",
        json={"bot_id": 999999999, "guest_user_id": 999999999},
        headers=headers,
    )

    assert_error(response, 404, "not found")


def test_check_golden_path_assigned(
    http_client, api_base_url, create_user, create_bot, create_bot_assignment, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    create_bot_assignment(bot.id, guest.id, parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.post(
        f"{api_base_url}/bot-guest-assignment/check",
        json={"bot_id": bot.id, "guest_user_id": guest.id},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"is_assigned": True}


def test_check_not_assigned(http_client, api_base_url, create_user, create_bot, login):
    parent, parent_password = create_user(role=USER_ROLE)
    bot = create_bot(parent.id)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.post(
        f"{api_base_url}/bot-guest-assignment/check",
        json={"bot_id": bot.id, "guest_user_id": guest.id},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"is_assigned": False}
