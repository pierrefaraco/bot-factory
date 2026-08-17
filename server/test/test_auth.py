"""HTTP regression tests for /api/auth/* (rest_authent.py)."""

import pytest

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


def test_refresh_golden_path(http_client, api_base_url, create_user, login):
    user, password = create_user()
    headers = login(user.mail, password)

    # The blueprint's before_request hook requires application/json on every
    # POST, even for body-less routes like this one, so json={} is needed to
    # get past it and reach the actual @jwt_required() check.
    response = http_client.post(f"{api_base_url}/auth/refresh", json={}, headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body.get("access_token"), str) and body["access_token"]


def test_refresh_without_token(http_client, api_base_url):
    response = http_client.post(f"{api_base_url}/auth/refresh", json={})

    assert_error(response, 401)


def test_logout_golden_path(http_client, api_base_url, create_user, login):
    user, password = create_user()
    headers = login(user.mail, password)

    response = http_client.post(f"{api_base_url}/auth/logout", json={}, headers=headers)

    assert response.status_code == 200, response.text
    assert response.json() == {"message": "Logged out successfully"}


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
