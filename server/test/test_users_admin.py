"""HTTP regression tests for /api/users/* (rest_users_admin.py).

This is the largest blueprint (~25 routes) and the reference for the
self/guest/admin role-matrix pattern reused by later blueprints.
"""

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dao.database import User

from .helpers import assert_error, unique


def test_register_golden_path(http_client, api_base_url, track):
    email = unique("newuser") + "@example.com"

    response = http_client.post(
        f"{api_base_url}/users",
        json={"name": "New User", "email": email, "password": "Passw0rd!23"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["message"] == "User registered successfully"
    assert body["user"]["email"] == email
    track(User, body["user"]["id"])


def test_register_duplicate_email(http_client, api_base_url, create_user):
    user, _password = create_user()

    response = http_client.post(
        f"{api_base_url}/users",
        json={"name": "Dup", "email": user.mail, "password": "Passw0rd!23"},
    )

    assert_error(response, 409, "already registered")


def test_register_missing_content_type(http_client, api_base_url):
    # Unlike rest_authent.py (which has a blueprint-level before_request
    # hook checking Content-Type ahead of everything else), this blueprint
    # has no such hook, so a non-JSON Content-Type reaches spectree's own
    # @api.validate() first: it can't parse the body as JSON regardless of
    # what's in it, so Pydantic reports every field as missing rather than
    # the handler's own "Content-Type must be application/json" message
    # (that check is effectively dead code for this route).
    response = http_client.post(
        f"{api_base_url}/users",
        data='{"name": "X", "email": "x@example.com", "password": "x"}',
        headers={"Content-Type": "text/plain"},
    )

    assert_error(response, 400, "Field required")


def test_register_validation_error(http_client, api_base_url):
    response = http_client.post(
        f"{api_base_url}/users",
        json={"name": "", "email": "not-an-email", "password": "x"},
    )

    assert_error(response, 400)


def test_register_guest_without_assigned_bots_golden_path(
    http_client, api_base_url, create_user, login, db_session, track
):
    parent, parent_password = create_user(role=USER_ROLE)
    headers = login(parent.mail, parent_password)
    email = unique("newguest") + "@example.com"

    response = http_client.post(
        f"{api_base_url}/users/guest",
        json={"name": "New Guest", "email": email, "password": "Passw0rd!23"},
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json() == {"message": "Guest user registered successfully"}
    created = db_session.query(User).filter_by(mail=email).first()
    track(User, created.id)


def test_register_guest_golden_path(
    http_client, api_base_url, create_user, login, db_session, track
):
    parent, parent_password = create_user(role=USER_ROLE)
    headers = login(parent.mail, parent_password)
    email = unique("newguest") + "@example.com"

    response = http_client.post(
        f"{api_base_url}/users/guest",
        json={
            "name": "New Guest",
            "email": email,
            "password": "Passw0rd!23",
            "assigned_bot_ids": [],
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json() == {"message": "Guest user registered successfully"}
    created = db_session.query(User).filter_by(mail=email).first()
    track(User, created.id)


def test_register_guest_duplicate_email(
    http_client, api_base_url, create_user, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    headers = login(parent.mail, parent_password)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)

    response = http_client.post(
        f"{api_base_url}/users/guest",
        json={"name": "Dup", "email": guest.mail, "password": "Passw0rd!23"},
        headers=headers,
    )

    assert_error(response, 409, "already registered")


def test_register_guest_requires_auth(http_client, api_base_url):
    response = http_client.post(
        f"{api_base_url}/users/guest",
        json={"name": "X", "email": "x@example.com", "password": "Passw0rd!23"},
    )

    assert_error(response, 401)


def test_update_self_golden_path(http_client, api_base_url, create_user, login):
    user, password = create_user()
    headers = login(user.mail, password)
    new_name = unique("Renamed")

    response = http_client.put(
        f"{api_base_url}/users/self", json={"name": new_name}, headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["name"] == new_name


def test_update_self_requires_auth(http_client, api_base_url):
    response = http_client.put(f"{api_base_url}/users/self", json={"name": "X"})

    assert_error(response, 401)


def test_update_guest_golden_path(http_client, api_base_url, create_user, login):
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    headers = login(parent.mail, parent_password)
    new_name = unique("Renamed")

    response = http_client.put(
        f"{api_base_url}/users/guest/{guest.id}",
        json={"name": new_name},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["name"] == new_name


def test_update_guest_not_owned(http_client, api_base_url, create_user, login):
    stranger, stranger_password = create_user(role=USER_ROLE)
    other_parent, _other_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=other_parent.id)
    headers = login(stranger.mail, stranger_password)

    response = http_client.put(
        f"{api_base_url}/users/guest/{guest.id}",
        json={"name": "X"},
        headers=headers,
    )

    assert_error(response, 403, "not your guest")


def test_update_guest_not_found(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.put(
        f"{api_base_url}/users/guest/999999999", json={"name": "X"}, headers=headers
    )

    assert_error(response, 404, "not found")


def test_update_admin_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user()
    headers = login(admin.mail, admin_password)
    new_name = unique("Renamed")

    response = http_client.put(
        f"{api_base_url}/users/{target.id}", json={"name": new_name}, headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["name"] == new_name


def test_update_admin_forbidden_for_non_admin(
    http_client, api_base_url, create_user, login
):
    user, password = create_user(role=USER_ROLE)
    target, _target_password = create_user()
    headers = login(user.mail, password)

    response = http_client.put(
        f"{api_base_url}/users/{target.id}", json={"name": "X"}, headers=headers
    )

    assert_error(response, 403, "Access denied")


def test_get_all_users_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(f"{api_base_url}/users", headers=headers)

    assert response.status_code == 200, response.text
    assert isinstance(response.json()["users"], list)


def test_get_all_users_forbidden_for_non_admin(
    http_client, api_base_url, create_user, login
):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/users", headers=headers)

    assert_error(response, 403, "Access denied")


def test_get_all_guests_golden_path(http_client, api_base_url, create_user, login):
    parent, parent_password = create_user(role=USER_ROLE)
    create_user(role=GUEST_ROLE, parent_id=parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.get(f"{api_base_url}/users/guests", headers=headers)

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_get_users_by_role_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(f"{api_base_url}/users/role/{USER_ROLE}", headers=headers)

    assert response.status_code == 200, response.text
    assert isinstance(response.json()["users"], list)


def test_get_users_by_role_invalid_role(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(
        f"{api_base_url}/users/role/NotARole", headers=headers
    )

    assert_error(response, 400, "Invalid role")


def test_get_children_self_golden_path(http_client, api_base_url, create_user, login):
    parent, parent_password = create_user(role=USER_ROLE)
    create_user(role=GUEST_ROLE, parent_id=parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.get(f"{api_base_url}/users/children/self", headers=headers)

    assert response.status_code == 200, response.text
    assert isinstance(response.json()["children"], list)


def test_get_children_admin_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    parent, _parent_password = create_user(role=USER_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(
        f"{api_base_url}/users/children/{parent.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json()["children"], list)


def test_delete_self_golden_path(http_client, api_base_url, create_user, login):
    # Deliberately not using the registry-tracked create_user fixture's
    # cleanup path for the assertion — the endpoint itself deletes the row,
    # so the registry's own DELETE at teardown will simply affect 0 rows.
    user, password = create_user()
    headers = login(user.mail, password)

    response = http_client.delete(f"{api_base_url}/users/self", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["msg"] == "User deleted successfully"


def test_delete_guest_owned(http_client, api_base_url, create_user, login):
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.delete(
        f"{api_base_url}/users/guest/{guest.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["msg"] == "User deleted successfully"


def test_delete_guest_not_owned(http_client, api_base_url, create_user, login):
    stranger, stranger_password = create_user(role=USER_ROLE)
    other_parent, _other_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=other_parent.id)
    headers = login(stranger.mail, stranger_password)

    response = http_client.delete(
        f"{api_base_url}/users/guest/{guest.id}", headers=headers
    )

    assert_error(response, 403, "not your guest")


def test_delete_admin_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user()
    headers = login(admin.mail, admin_password)

    response = http_client.delete(f"{api_base_url}/users/{target.id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["msg"] == "User deleted successfully"


def test_delete_admin_not_found(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.delete(
        f"{api_base_url}/users/999999999", headers=headers
    )

    assert_error(response, 404, "not found")


def test_change_role_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user(role=USER_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.put(
        f"{api_base_url}/users/{target.id}/role",
        json={"role": GUEST_ROLE},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["roles"] == GUEST_ROLE


def test_change_role_invalid_role_value(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user(role=USER_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.put(
        f"{api_base_url}/users/{target.id}/role",
        json={"role": "NotARole"},
        headers=headers,
    )

    assert_error(response, 400)


def test_change_password_self_golden_path(http_client, api_base_url, create_user, login):
    user, password = create_user()
    headers = login(user.mail, password)

    response = http_client.put(
        f"{api_base_url}/users/password/self",
        json={"old_password": password, "new_password": "NewPassw0rd!45"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["msg"] == "Password updated successfully"


def test_change_password_self_wrong_old_password(
    http_client, api_base_url, create_user, login
):
    user, password = create_user()
    headers = login(user.mail, password)

    response = http_client.put(
        f"{api_base_url}/users/password/self",
        json={"old_password": "wrong", "new_password": "NewPassw0rd!45"},
        headers=headers,
    )

    assert_error(response, 401, "Invalid old password")


def test_change_password_self_same_as_old(http_client, api_base_url, create_user, login):
    user, password = create_user()
    headers = login(user.mail, password)

    response = http_client.put(
        f"{api_base_url}/users/password/self",
        json={"old_password": password, "new_password": password},
        headers=headers,
    )

    assert_error(response, 400, "equal old password")


def test_deactivate_admin_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user()
    headers = login(admin.mail, admin_password)

    response = http_client.put(
        f"{api_base_url}/users/{target.id}/deactivate", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["is_active"] is False


def test_activate_admin_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user(is_active=False)
    headers = login(admin.mail, admin_password)

    response = http_client.put(
        f"{api_base_url}/users/{target.id}/activate", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["is_active"] is True


def test_deactivate_guest_owned(http_client, api_base_url, create_user, login):
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.put(
        f"{api_base_url}/users/{guest.id}/deactivate/guest", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["is_active"] is False


def test_activate_guest_owned(http_client, api_base_url, create_user, login):
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(
        role=GUEST_ROLE, parent_id=parent.id, is_active=False
    )
    headers = login(parent.mail, parent_password)

    response = http_client.put(
        f"{api_base_url}/users/{guest.id}/activate/guest", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["is_active"] is True


def test_reassign_children_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    old_parent, _old_password = create_user(role=USER_ROLE)
    new_parent, _new_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=old_parent.id)
    headers = login(admin.mail, admin_password)

    response = http_client.put(
        f"{api_base_url}/users/reassign-children",
        json={"old_parent_id": old_parent.id, "new_parent_id": new_parent.id},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["msg"] == "Children reassigned successfully"


def test_get_self_golden_path(http_client, api_base_url, create_user, login):
    user, password = create_user()
    headers = login(user.mail, password)

    response = http_client.get(f"{api_base_url}/users/self", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["email"] == user.mail


def test_get_admin_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user()
    headers = login(admin.mail, admin_password)

    response = http_client.get(f"{api_base_url}/users/{target.id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["email"] == target.mail


def test_get_admin_not_found(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    headers = login(admin.mail, admin_password)

    response = http_client.get(f"{api_base_url}/users/999999999", headers=headers)

    assert_error(response, 404, "not found")


def test_get_guest_golden_path(http_client, api_base_url, create_user, login):
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.get(
        f"{api_base_url}/users/guest/{guest.id}", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["email"] == guest.mail


def test_get_guest_not_owned(http_client, api_base_url, create_user, login):
    stranger, stranger_password = create_user(role=USER_ROLE)
    other_parent, _other_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=other_parent.id)
    headers = login(stranger.mail, stranger_password)

    response = http_client.get(
        f"{api_base_url}/users/guest/{guest.id}", headers=headers
    )

    assert_error(response, 403, "not your guest")


def test_get_guest_not_found(http_client, api_base_url, create_user, login):
    user, password = create_user(role=USER_ROLE)
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/users/guest/999999999", headers=headers
    )

    assert_error(response, 404, "not found")


def test_patch_self_golden_path(http_client, api_base_url, create_user, create_bot, login):
    user, password = create_user()
    bot = create_bot(user.id)
    headers = login(user.mail, password)

    response = http_client.patch(
        f"{api_base_url}/users/self",
        json={"selected_bot_id": bot.id},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["selected_bot_id"] == bot.id


def test_patch_guest_golden_path(
    http_client, api_base_url, create_user, create_bot, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    bot = create_bot(parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.patch(
        f"{api_base_url}/users/guest/{guest.id}",
        json={"selected_bot_id": bot.id},
        headers=headers,
    )

    assert response.status_code == 200, response.text


def test_patch_guest_not_owned(http_client, api_base_url, create_user, login):
    stranger, stranger_password = create_user(role=USER_ROLE)
    other_parent, _other_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=other_parent.id)
    headers = login(stranger.mail, stranger_password)

    response = http_client.patch(
        f"{api_base_url}/users/guest/{guest.id}", json={}, headers=headers
    )

    assert_error(response, 403, "not your guest")


def test_patch_admin_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user()
    headers = login(admin.mail, admin_password)

    response = http_client.patch(
        f"{api_base_url}/users/{target.id}", json={}, headers=headers
    )

    assert response.status_code == 200, response.text


def test_get_selected_bot_self_golden_path(http_client, api_base_url, create_user, login):
    user, password = create_user()
    headers = login(user.mail, password)

    response = http_client.get(
        f"{api_base_url}/users/selected_bot/self", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"selected_bot_id": None, "bot": None}


def test_get_selected_bot_guest_golden_path(
    http_client, api_base_url, create_user, login
):
    parent, parent_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=parent.id)
    headers = login(parent.mail, parent_password)

    response = http_client.get(
        f"{api_base_url}/users/selected_bot/guest/{guest.id}", headers=headers
    )

    assert response.status_code == 200, response.text


def test_get_selected_bot_guest_not_owned(http_client, api_base_url, create_user, login):
    stranger, stranger_password = create_user(role=USER_ROLE)
    other_parent, _other_password = create_user(role=USER_ROLE)
    guest, _guest_password = create_user(role=GUEST_ROLE, parent_id=other_parent.id)
    headers = login(stranger.mail, stranger_password)

    response = http_client.get(
        f"{api_base_url}/users/selected_bot/guest/{guest.id}", headers=headers
    )

    assert_error(response, 403, "not your guest")


def test_get_selected_bot_admin_golden_path(
    http_client, api_base_url, create_user, login
):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    target, _target_password = create_user()
    headers = login(admin.mail, admin_password)

    response = http_client.get(
        f"{api_base_url}/users/selected_bot/{target.id}", headers=headers
    )

    assert response.status_code == 200, response.text
