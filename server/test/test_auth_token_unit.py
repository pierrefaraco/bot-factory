import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials

from src.config.config import AppConfig
from src.dependencies import auth
from src.exceptions.api_error import ApiError

SECRET = "unit-test-secret-" + "x" * 32


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setattr(AppConfig, "JWT_SECRET_KEY", SECRET)
    monkeypatch.setattr(AppConfig, "JWT_ACCESS_TOKEN_EXPIRES", 3600)


@asynccontextmanager
async def _no_db_scope():
    yield


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_token_lifetime_is_jwt_access_token_expires():
    claims = auth.decode_access_token(auth.issue_access_token(7, "User", "a@b.c"))
    assert claims["sub"] == "7"
    assert claims["roles"] == "User" and claims["mail"] == "a@b.c"
    assert claims["exp"] - claims["iat"] == 3600


def test_expired_token_rejected():
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    token = jwt.encode(
        {"sub": "1", "jti": "j", "exp": past}, SECRET, algorithm=auth.JWT_ALGORITHM
    )
    with pytest.raises(ApiError, match="expired"):
        auth.decode_access_token(token)


def test_token_signed_with_another_key_rejected():
    token = jwt.encode(
        {"sub": "1", "jti": "j", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "another-key-" + "y" * 32,
        algorithm=auth.JWT_ALGORITHM,
    )
    with pytest.raises(ApiError, match="Invalid token"):
        auth.decode_access_token(token)


def test_token_without_jti_rejected():
    token = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        SECRET,
        algorithm=auth.JWT_ALGORITHM,
    )
    with pytest.raises(ApiError, match="Invalid token"):
        auth.decode_access_token(token)


@pytest.mark.parametrize("revoked", [False, True])
def test_get_current_claims_checks_revocation(revoked):
    token = auth.issue_access_token(1, "User", "a@b.c")
    with patch.object(auth, "async_db_session_scope", _no_db_scope), patch.object(
        auth.RevokedTokenRepository, "is_revoked", AsyncMock(return_value=revoked)
    ):
        if revoked:
            with pytest.raises(ApiError, match="revoked"):
                asyncio.run(auth.get_current_claims(_bearer(token)))
        else:
            assert (asyncio.run(auth.get_current_claims(_bearer(token))))["sub"] == "1"
