"""JWT issuing/verification for native FastAPI routes -- the full
replacement for Flask-JWT-Extended (encode side: create_access_token
below; decode side: decode_access_token/get_current_claims/require_roles,
originally written for role_required.py, itself now retired).

create_access_token() replicates Flask-JWT-Extended's own default claim
shape exactly (HS256, JWT_IDENTITY_CLAIM="sub", JWT_ENCODE_NBF=True,
fresh=False, type="access", a fresh uuid4 jti) so tokens this issues
decode identically via decode_access_token() below. Flask-JWT-Extended's
own create_access_token() needed a Flask app context (it reads
JWT_SECRET_KEY etc. off current_app.config) -- gone now that nothing
mounts a Flask app anymore (see ai_server/main.py's own history/removal).

Revocation is checked against authent_svc's own module-level
REVOKED_JWT_LIST -- imported live (not copied) inside get_current_claims,
since both this and authent_svc.py's logout() run in the same process
(the import is deferred to call time there, not module level, since
authent_svc.py imports create_access_token from this module -- a
module-level import back here would be circular).
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from ai_server.config.config import AppConfig
from ai_server.exceptions.api_error import ApiError

JWT_ALGORITHM = "HS256"


def create_access_token(
    identity, additional_claims: Optional[dict] = None, expires_delta: Optional[timedelta] = None
) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "fresh": False,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "access",
        "sub": identity,
        "nbf": now,
    }
    if expires_delta:
        claims["exp"] = now + expires_delta
    if additional_claims:
        claims.update(additional_claims)
    return jwt.encode(claims, AppConfig.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# auto_error=False: HTTPBearer's default behavior raises a 403 "Not
# authenticated" HTTPException when the header is missing/malformed --
# Flask-JWT-Extended's jwt_required() (and the existing test suite) both
# expect 401 here instead, so that case is handled explicitly below.
bearer_scheme = HTTPBearer(auto_error=False)


def decode_access_token(token: str) -> dict:
    """Same validation flask_jwt_extended's @jwt_required() performs:
    signature + exp. Raises ApiError(401) on failure, mirroring
    role_required's error contract."""
    try:
        return jwt.decode(token, AppConfig.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except ExpiredSignatureError as exc:
        raise ApiError("Token has expired", status_code=401) from exc
    except JWTError as exc:
        raise ApiError("Invalid token", status_code=401) from exc


def get_current_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """Depends() replacement for @jwt_required() + get_jwt()."""
    if credentials is None:
        raise ApiError("Missing Authorization Header", status_code=401)
    claims = decode_access_token(credentials.credentials)
    # Lazy import: authent_svc.py imports create_access_token from this
    # module, so importing it back at module level here would be circular.
    from ai_server.services import authent_svc

    if claims.get("jti") in authent_svc.REVOKED_JWT_LIST:
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
