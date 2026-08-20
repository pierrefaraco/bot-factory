"""Authentication REST API -- native FastAPI port of the former
ai_server/rest/rest_authent.py Flask blueprint (Phase 9, the last
blueprint of the Flask -> FastAPI migration). Same URLs, same response
shapes.

This blueprint had a real @bp.before_request Content-Type guard
(unlike avatar/bot_parameters/bot_assignment/knowledge/users_admin,
which never had one) that ran before SpecTree/the handler either way --
require_json_content_type() reproduces that unconditional check exactly,
same as bot_router.py's POST/PUT routes.

refresh()/logout() use get_current_claims (any authenticated user, no
role restriction) rather than require_roles(...): the original used
plain @jwt_required() with no role check at all. Both routes needed a
small AuthenticationService refactor (see authent_svc.py) since
refresh_token()/logout() used to read the jti/identity straight off
Flask-JWT-Extended's own token context via get_jwt()/get_jwt_identity()
-- unavailable to a native route that never ran @jwt_required().

Anti-enumeration: login()'s AuthenticationError/NotFoundError (wrong
password, inactive account, unknown email) all collapse to the same
"Invalid email or password" 401, same as the original.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from ai_server.dependencies.auth import get_current_claims
from ai_server.dependencies.content_type import require_json_content_type
from ai_server.dependencies.db_session import with_db_session
from ai_server.exceptions.api_error import ApiError
from ai_server.exceptions.service_exceptions import AuthenticationError, NotFoundError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.authent_svc import AuthenticationService
from ai_server.services.google_authent_svc import GoogleAuthentSvc

router = APIRouter(prefix="/api/auth", tags=["auth"])

app_logger = BotFactoryLogger()
auth_svc = AuthenticationService()
google_auth_svc = GoogleAuthentSvc()


class LoginRequest(BaseModel):
    """Schema for login validation"""

    email: EmailStr
    password: str = Field(min_length=1)


class GoogleOAuthRequest(BaseModel):
    """Schema for Google OAuth login validation"""

    credential: str = Field(min_length=1)


@router.post("/login", dependencies=[Depends(require_json_content_type)])
@with_db_session
def login(body: LoginRequest):
    """User login with email and password. Returns a JWT access token."""
    app_logger.info("POST /auth/login - login called")
    app_logger.info(f"User attempting login with email: {body.email}")
    try:
        access_token = auth_svc.login(body.email, body.password)
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
@with_db_session
def login_with_google(body: GoogleOAuthRequest):
    """User login with a Google OAuth credential. Returns a JWT access token."""
    app_logger.info("POST /auth/google - login_with_google called")
    # Never log the raw OAuth credential (it's a bearer token), only that
    # one was received.
    app_logger.info("User attempting login with Google OAuth credential")

    access_token = google_auth_svc.verify_google_token(body.credential)
    if access_token is None:
        app_logger.warning("Failed login attempt with Google OAuth credential")
        raise ApiError("Invalid email or password", status_code=401)

    app_logger.info("Successful login with Google OAuth credential")
    return {"token": access_token}


@router.post("/refresh", dependencies=[Depends(require_json_content_type)])
@with_db_session
def refresh(claims: dict = Depends(get_current_claims)):
    """Refresh JWT access token"""
    user_id = claims["sub"]
    app_logger.info(f"POST /auth/refresh - refresh called for user_id={user_id}")
    access_token = auth_svc.refresh_token(claims["jti"], user_id)
    app_logger.info(f"Token refresh succeeded for user_id={user_id}")
    return {"access_token": access_token}


@router.post("/logout", dependencies=[Depends(require_json_content_type)])
@with_db_session
def logout(claims: dict = Depends(get_current_claims)):
    """User logout"""
    app_logger.info("POST /auth/logout - logout called")
    user_id = claims["sub"]
    app_logger.info(f"User {user_id} logging out")
    auth_svc.logout(claims["jti"])
    app_logger.info(f"User {user_id} logged out successfully")
    return {"message": "Logged out successfully"}
