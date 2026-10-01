"""JWT access tokens: issuing (issue_access_token), and the Depends()
guards that check them (get_current_claims, require_roles,
reject_demo_account).

Tokens are HS256-signed with JWT_SECRET_KEY and expire after
JWT_ACCESS_TOKEN_EXPIRES seconds. Logout revokes a token by its jti in
the revoked_token table (RevokedTokenRepository), which every API worker
sees and which survives restarts.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config.config import AppConfig
from src.database.session import async_db_session_scope
from src.exceptions.api_error import ApiError
from src.repositories.revoked_token_repository import RevokedTokenRepository

JWT_ALGORITHM = "HS256"


def issue_access_token(user_id: int, roles: str, mail: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(seconds=AppConfig.JWT_ACCESS_TOKEN_EXPIRES),
        "roles": roles,
        "mail": mail,
    }
    return jwt.encode(claims, AppConfig.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# auto_error=False: HTTPBearer would answer a missing header with a 403;
# this API answers 401 (see get_current_claims).
bearer_scheme = HTTPBearer(auto_error=False)


def decode_access_token(token: str) -> dict:
    """Checks signature, expiry and required claims. Raises ApiError(401)."""
    try:
        return jwt.decode(
            token,
            AppConfig.JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ApiError("Token has expired", status_code=401) from exc
    except jwt.InvalidTokenError as exc:
        raise ApiError("Invalid token", status_code=401) from exc


async def get_current_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """Claims of the request's valid, unrevoked bearer token."""
    if credentials is None:
        raise ApiError("Missing Authorization Header", status_code=401)
    claims = decode_access_token(credentials.credentials)
    # A scope of its own: works whether or not the router opened one.
    async with async_db_session_scope():
        revoked = await RevokedTokenRepository().is_revoked(claims["jti"])
    if revoked:
        raise ApiError("Token has been revoked", status_code=401)
    return claims


def require_roles(roles: list):
    """Depends() replacement for @role_required(roles)."""

    def dependency(claims: dict = Depends(get_current_claims)) -> dict:
        current_roles = claims.get("roles", [])
        if not any(role in current_roles for role in roles):
            raise ApiError("Access denied", status_code=403)
        return claims

    return dependency


def reject_demo_account(claims: dict = Depends(get_current_claims)) -> dict:
    """Refuses routes that change the account itself (delete it, rename it,
    change its email or password, add guests to it) to the shared demo
    account: anyone can log into it from the landing page (POST
    /api/auth/demo), and one visitor must not be able to break it for the
    next ones. Matched on the JWT's mail claim, so it holds however the
    session was opened. An admin can still manage it through the
    /users/<id> routes."""
    demo_mail = AppConfig.DEMO_ACCOUNT_EMAIL
    if demo_mail and claims.get("mail", "").lower() == demo_mail.lower():
        raise ApiError("Not available with the demo account", status_code=403)
    return claims
