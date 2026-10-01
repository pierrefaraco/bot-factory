"""HTTP regression tests for /api/auth/* (authent_router.py)."""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from src.config.constant import ADMIN_ROLE, USER_ROLE
from src.models import MagicLink, User

from .helpers import assert_error


def test_login_golden_path(http_client, api_base_url, create_user):
    user, password = create_user()

    response = http_client.post(
        f"{api_base_url}/auth/login", json={"email": user.mail, "password": password}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body.get("token"), str) and body["token"]


def test_login_wrong_password(http_client, api_base_url, create_user):
    user, _password = create_user()

    response = http_client.post(
        f"{api_base_url}/auth/login",
        json={"email": user.mail, "password": "wrong-password"},
    )

    assert_error(response, 401, "Invalid email or password")


def test_login_unknown_user(http_client, api_base_url):
    response = http_client.post(
        f"{api_base_url}/auth/login",
        json={"email": "no-such-user@example.com", "password": "whatever"},
    )

    assert_error(response, 401, "Invalid email or password")


def test_login_missing_content_type(http_client, api_base_url, create_user):
    user, password = create_user()

    response = http_client.post(
        f"{api_base_url}/auth/login",
        data=f'{{"email": "{user.mail}", "password": "{password}"}}',
        headers={"Content-Type": "text/plain"},
    )

    assert_error(response, 400, "Content-Type")


def test_login_validation_error_empty_password(http_client, api_base_url, create_user):
    user, _password = create_user()

    response = http_client.post(
        f"{api_base_url}/auth/login", json={"email": user.mail, "password": ""}
    )

    assert_error(response, 400)


def test_login_validation_error_bad_email(http_client, api_base_url):
    response = http_client.post(
        f"{api_base_url}/auth/login",
        json={"email": "not-an-email", "password": "whatever"},
    )

    assert_error(response, 400)


def test_logout_golden_path(http_client, api_base_url, create_user, login):
    user, password = create_user()
    headers = login(user.mail, password)

    response = http_client.post(f"{api_base_url}/auth/logout", json={}, headers=headers)

    assert response.status_code == 200, response.text
    assert response.json() == {"message": "Logged out successfully"}

    # The revocation is stored in the database, not in one worker's memory.
    response = http_client.get(f"{api_base_url}/users/me", headers=headers)
    assert_error(response, 401)


def test_logout_without_token(http_client, api_base_url):
    response = http_client.post(f"{api_base_url}/auth/logout", json={})

    assert_error(response, 401)


def test_google_login_missing_credential(http_client, api_base_url):
    response = http_client.post(f"{api_base_url}/auth/google", json={"credential": ""})

    assert_error(response, 400)


def test_google_login_invalid_credential(http_client, api_base_url):
    # A malformed (non-JWT-shaped) string fails google-auth's local structure
    # check before it would attempt any network call to Google's cert
    # endpoint, so this stays deterministic and offline.
    response = http_client.post(
        f"{api_base_url}/auth/google", json={"credential": "not-a-real-google-token"}
    )

    assert_error(response, 401, "Invalid email or password")


@pytest.mark.skip(
    reason="Requires a real Google-issued ID token; cannot be minted black-box in tests."
)
def test_google_login_golden_path():
    pass


# --- One-time login links (/auth/magic-links, /auth/magic-link) -------------


def _create_magic_link(http_client, api_base_url, headers, email, **extra):
    return http_client.post(
        f"{api_base_url}/auth/magic-links", json={"email": email, **extra}, headers=headers
    )


def _token_from_url(url: str) -> str:
    return parse_qs(urlparse(url).query)["token"][0]


def _insert_magic_link(db_session, user_id, expires_at):
    """Creates a link straight in the DB, for states the API can't produce
    on demand (already expired)."""
    token = secrets.token_urlsafe(32)
    db_session.add(
        MagicLink(user_id, hashlib.sha256(token.encode()).hexdigest(), expires_at)
    )
    db_session.commit()
    return token


def test_magic_link_golden_path(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    user, _password = create_user()

    response = _create_magic_link(
        http_client, api_base_url, login(admin.mail, admin_password), user.mail
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert urlparse(body["url"]).path == "/auth"
    assert body["expires_at"]

    response = http_client.post(
        f"{api_base_url}/auth/magic-link", json={"token": _token_from_url(body["url"])}
    )
    assert response.status_code == 200, response.text
    jwt_token = response.json()["token"]

    # The JWT is a regular session token for that user.
    response = http_client.get(
        f"{api_base_url}/users/me",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert response.status_code == 200, response.text


def test_magic_link_is_single_use(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    user, _password = create_user()
    url = _create_magic_link(
        http_client, api_base_url, login(admin.mail, admin_password), user.mail
    ).json()["url"]
    token = _token_from_url(url)

    first = http_client.post(f"{api_base_url}/auth/magic-link", json={"token": token})
    second = http_client.post(f"{api_base_url}/auth/magic-link", json={"token": token})

    assert first.status_code == 200, first.text
    assert_error(second, 401, "Invalid or expired link")


def test_magic_link_expired(http_client, api_base_url, db_session, create_user):
    user, _password = create_user()
    token = _insert_magic_link(
        db_session, user.id, datetime.now(timezone.utc) - timedelta(minutes=1)
    )

    response = http_client.post(f"{api_base_url}/auth/magic-link", json={"token": token})

    assert_error(response, 401, "Invalid or expired link")


def test_magic_link_inactive_user(http_client, api_base_url, db_session, create_user):
    user, _password = create_user(is_active=False)
    token = _insert_magic_link(
        db_session, user.id, datetime.now(timezone.utc) + timedelta(hours=1)
    )

    response = http_client.post(f"{api_base_url}/auth/magic-link", json={"token": token})

    assert_error(response, 401, "Invalid or expired link")


def test_magic_link_unknown_token(http_client, api_base_url):
    response = http_client.post(
        f"{api_base_url}/auth/magic-link", json={"token": "no-such-token"}
    )

    assert_error(response, 401, "Invalid or expired link")


def test_magic_link_create_requires_admin(http_client, api_base_url, create_user, login):
    user, password = create_user()

    response = _create_magic_link(
        http_client, api_base_url, login(user.mail, password), user.mail
    )

    assert_error(response, 403)


def test_magic_link_create_unknown_email(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)

    response = _create_magic_link(
        http_client,
        api_base_url,
        login(admin.mail, admin_password),
        "no-such-user@example.com",
    )

    assert_error(response, 404)


def test_magic_link_create_inactive_user(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)
    user, _password = create_user(is_active=False)

    response = _create_magic_link(
        http_client, api_base_url, login(admin.mail, admin_password), user.mail
    )

    assert_error(response, 409)


def test_magic_link_create_ttl_out_of_range(http_client, api_base_url, create_user, login):
    admin, admin_password = create_user(role=ADMIN_ROLE)

    response = _create_magic_link(
        http_client, api_base_url, login(admin.mail, admin_password), admin.mail, ttl_hours=0
    )

    assert_error(response, 400)


# --- Shared demo account (/auth/demo) ---------------------------------------
# Needs the api started with DEMO_ACCOUNT_EMAIL set, and the same value in
# TEST_DEMO_ACCOUNT_EMAIL (docker-compose.test.yml sets both).

DEMO_ACCOUNT_EMAIL = os.environ.get("TEST_DEMO_ACCOUNT_EMAIL", "")

requires_demo = pytest.mark.skipif(
    not DEMO_ACCOUNT_EMAIL, reason="TEST_DEMO_ACCOUNT_EMAIL not set"
)


@pytest.fixture()
def create_demo_account(db_session, create_user):
    """The demo account, created with the given role/state. Any leftover from
    an interrupted run is removed first: its email is fixed, not random."""
    db_session.query(User).filter(User.mail == DEMO_ACCOUNT_EMAIL).delete()
    db_session.commit()

    def _create(role=USER_ROLE, is_active=True):
        user, _password = create_user(role=role, is_active=is_active, mail=DEMO_ACCOUNT_EMAIL)
        return user

    return _create


def _demo_login(http_client, api_base_url):
    return http_client.post(f"{api_base_url}/auth/demo", json={})


@requires_demo
def test_demo_status_enabled(http_client, api_base_url):
    response = http_client.get(f"{api_base_url}/auth/demo")

    assert response.status_code == 200, response.text
    assert response.json() == {"enabled": True}


@requires_demo
def test_demo_login_golden_path(http_client, api_base_url, create_demo_account):
    create_demo_account()

    response = _demo_login(http_client, api_base_url)

    assert response.status_code == 200, response.text
    headers = {"Authorization": f"Bearer {response.json()['token']}"}
    response = http_client.get(f"{api_base_url}/users/me", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["email"] == DEMO_ACCOUNT_EMAIL


@requires_demo
def test_demo_login_missing_account(http_client, api_base_url, create_demo_account):
    # The fixture only clears leftovers here: no account is created.
    response = _demo_login(http_client, api_base_url)

    assert_error(response, 404, "Demo is not available")


@requires_demo
def test_demo_login_inactive_account(http_client, api_base_url, create_demo_account):
    create_demo_account(is_active=False)

    response = _demo_login(http_client, api_base_url)

    assert_error(response, 404, "Demo is not available")


@requires_demo
def test_demo_login_refuses_admin_account(http_client, api_base_url, create_demo_account):
    create_demo_account(role=ADMIN_ROLE)

    response = _demo_login(http_client, api_base_url)

    assert_error(response, 404, "Demo is not available")


@requires_demo
@pytest.mark.parametrize(
    "method, path, body",
    [
        ("delete", "/users/me", None),
        ("put", "/users/me", {"name": "hijacked"}),
        ("put", "/users/password/me", {"old_password": "a", "new_password": "b"}),
        ("post", "/users/guest", {"name": "g", "email": "g@example.com", "password": "Passw0rd!23"}),
    ],
)
def test_demo_account_cannot_change_itself(
    http_client, api_base_url, create_demo_account, method, path, body
):
    create_demo_account()
    token = _demo_login(http_client, api_base_url).json()["token"]

    response = http_client.request(
        method,
        f"{api_base_url}{path}",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert_error(response, 403, "demo account")
