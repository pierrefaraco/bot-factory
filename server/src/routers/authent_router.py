"""Authentication REST API.

Anti-enumeration: a wrong password, an inactive account and an unknown
email all get the same "Invalid email or password" 401, on /login as on
/google.

Blocking work (password hashing, the HTTP fetch of Google's signing
certificates) runs through run_in_threadpool inside the services.

There is no refresh token: an access token lasts JWT_ACCESS_TOKEN_EXPIRES
seconds, after which the user logs in again.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from src.config.config import AppConfig
from src.config.constant import ADMIN_ROLE
from src.dependencies.auth import get_current_claims, require_roles
from src.dependencies.content_type import require_json_content_type
from src.dependencies.db_session import async_db_session_dependency
from src.dependencies.services import (
    AuthenticationServiceDep,
    GoogleAuthentServiceDep,
    MagicLinkServiceDep,
)
from src.exceptions.api_error import ApiError
from src.exceptions.service_exceptions import AuthenticationError, NotFoundError
from src.log.bot_factory_logger import BotFactoryLogger
from src.services.magic_link_svc import DEFAULT_TTL_HOURS, MAX_TTL_HOURS

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
    dependencies=[Depends(async_db_session_dependency)],
)

app_logger = BotFactoryLogger()


class LoginRequest(BaseModel):
    """Schema for login validation"""

    email: EmailStr
    password: str = Field(min_length=1)


class GoogleOAuthRequest(BaseModel):
    """Schema for Google OAuth login validation"""

    credential: str = Field(min_length=1)


@router.post("/login", dependencies=[Depends(require_json_content_type)])
async def login(body: LoginRequest, auth_svc: AuthenticationServiceDep):
    """User login with email and password. Returns a JWT access token."""
    app_logger.info("POST /auth/login - login called")
    app_logger.info(f"User attempting login with email: {body.email}")
    try:
        access_token = await auth_svc.login(body.email, body.password)
    except (AuthenticationError, NotFoundError) as exc:
        # Même message générique pour les deux cas (mauvais mot de passe vs
        # utilisateur inexistant), pour ne pas permettre l'énumération des
        # comptes existants.
        app_logger.warning(f"Failed login attempt: {exc}")
        raise ApiError("Invalid email or password", status_code=401) from exc

    if access_token is None:
        app_logger.warning(f"Failed login attempt for email: {body.email}")
        raise ApiError("Invalid email or password", status_code=401)

    app_logger.info(f"Successful login for email: {body.email}")
    return {"token": access_token}


@router.post("/google", dependencies=[Depends(require_json_content_type)])
async def login_with_google(
    body: GoogleOAuthRequest,
    google_auth_svc: GoogleAuthentServiceDep,
):
    """User login with a Google OAuth credential. Returns a JWT access token."""
    app_logger.info("POST /auth/google - login_with_google called")
    # Never log the raw OAuth credential (it's a bearer token), only that
    # one was received.
    app_logger.info("User attempting login with Google OAuth credential")

    try:
        access_token = await google_auth_svc.verify_google_token(body.credential)
    except AuthenticationError as exc:
        # Même message générique que /login (voir commentaire plus haut) :
        # un compte désactivé ne doit pas être distinguable d'un jeton invalide.
        app_logger.warning(f"Failed login attempt with Google OAuth credential: {exc}")
        raise ApiError("Invalid email or password", status_code=401) from exc

    if access_token is None:
        app_logger.warning("Failed login attempt with Google OAuth credential")
        raise ApiError("Invalid email or password", status_code=401)

    app_logger.info("Successful login with Google OAuth credential")
    return {"token": access_token}


class MagicLinkCreateRequest(BaseModel):
    """Schema for magic link creation"""

    email: EmailStr
    ttl_hours: int = Field(default=DEFAULT_TTL_HOURS, ge=1, le=MAX_TTL_HOURS)


class MagicLinkRedeemRequest(BaseModel):
    """Schema for magic link redemption"""

    token: str = Field(min_length=1, max_length=128)


@router.post("/magic-links", dependencies=[Depends(require_json_content_type)])
async def create_magic_link(
    body: MagicLinkCreateRequest,
    magic_link_svc: MagicLinkServiceDep,
    claims: dict = Depends(require_roles([ADMIN_ROLE])),
):
    """Admin only: creates a one-time login link for an existing account."""
    app_logger.info(f"POST /auth/magic-links - called by user_id={claims['sub']}")
    try:
        token, expires_at = await magic_link_svc.create(body.email, body.ttl_hours)
    except NotFoundError as exc:
        raise ApiError("User not found", status_code=404) from exc
    except AuthenticationError as exc:
        raise ApiError("User is not active", status_code=409) from exc
    return {
        "url": f"{AppConfig.PUBLIC_URL}/auth?token={token}",
        "expires_at": expires_at.isoformat(),
    }


@router.post("/magic-link", dependencies=[Depends(require_json_content_type)])
async def login_with_magic_link(
    body: MagicLinkRedeemRequest,
    magic_link_svc: MagicLinkServiceDep,
    auth_svc: AuthenticationServiceDep,
):
    """Redeems a one-time login link. Returns a JWT access token."""
    # Never log the token itself: until redeemed, it's a bearer credential.
    app_logger.info("POST /auth/magic-link - login_with_magic_link called")
    try:
        user = await magic_link_svc.redeem(body.token)
    except AuthenticationError as exc:
        app_logger.warning(f"Failed magic link login: {exc}")
        raise ApiError("Invalid or expired link", status_code=401) from exc
    return {"token": auth_svc.build_token(user)}


@router.get("/demo")
async def demo_status():
    """Whether the landing page's "Try the demo" login is available."""
    return {"enabled": bool(AppConfig.DEMO_ACCOUNT_EMAIL)}


@router.post("/demo", dependencies=[Depends(require_json_content_type)])
async def login_demo(auth_svc: AuthenticationServiceDep):
    """Password-free login into the shared demo account. Returns a JWT."""
    app_logger.info("POST /auth/demo - login_demo called")
    try:
        access_token = await auth_svc.login_demo()
    except (NotFoundError, AuthenticationError) as exc:
        # Misconfiguration on our side, not the visitor's: logged loudly,
        # answered with a plain "not available".
        app_logger.error(f"Demo login unavailable: {exc}")
        raise ApiError("Demo is not available", status_code=404) from exc
    return {"token": access_token}


@router.post("/logout", dependencies=[Depends(require_json_content_type)])
async def logout(
    auth_svc: AuthenticationServiceDep,
    claims: dict = Depends(get_current_claims),
):
    """User logout"""
    app_logger.info("POST /auth/logout - logout called")
    user_id = claims["sub"]
    app_logger.info(f"User {user_id} logging out")
    await auth_svc.logout(claims)
    app_logger.info(f"User {user_id} logged out successfully")
    return {"message": "Logged out successfully"}
