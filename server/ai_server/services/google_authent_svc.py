import datetime
from ai_server.exceptions.service_exceptions import AuthenticationError
from ai_server.services.base_service import BaseService
from google.oauth2 import id_token
from google.auth.transport import requests
from starlette.concurrency import run_in_threadpool
from ai_server.config.config import app_config
from ai_server.dependencies.auth import create_access_token
from ai_server.services.user_admin_svc import UserAdminService
from ai_server.dto.user_dto import UserDto


class GoogleAuthentSvc(BaseService):
    """Service for handling Google OAuth operations"""

    def __init__(self, user_admin_svc: UserAdminService):
        super().__init__()
        self.user_admin_svc = user_admin_svc

    async def verify_google_token(self, credential):
        try:
            # Blocking: fetches Google's signing certs over HTTP.
            id_info = await run_in_threadpool(
                id_token.verify_oauth2_token,
                credential,
                requests.Request(),
                app_config.GOOGLE_CLIENT_ID,
            )
            # Never log the full id_info payload: it carries PII (name,
            # picture, locale...) beyond what's needed for the audit trail.
            self.logger.info(f"Google OAuth token verified for email={id_info['email']}")

            user_dto = await self.user_admin_svc.get_user_by_email(id_info["email"])
            if not user_dto:
                user_dto = await self.record_user(id_info)
            if not user_dto.is_active:
                msg = (
                    f"User {user_dto.name} is not active, administrator can enable it."
                )
                self.logger.warning(msg)
                raise AuthenticationError(msg)

            self.logger.info(f"Google OAuth login succeeded for user_id={user_dto.id}")
            return self.build_token(user_dto)
        except ValueError as e:
            # Expected validation failure (invalid/expired Google token), not
            # a system error, and never log the credential/token value itself.
            self.logger.warning(f"Invalid Google OAuth token: {e}")
            return None

    async def record_user(self, id_info: dict) -> UserDto:
        self.logger.info(f"Auto-provisioning new user from Google OAuth: email={id_info['email']}")
        return await self.user_admin_svc.register_new_user(
            id_info["email"], id_info["name"], ""
        )

    def build_token(self, user: UserDto):
        expires = datetime.timedelta(minutes=3600)
        access_token = create_access_token(
            identity=f"{user.id}",
            additional_claims={"roles": user.roles, "mail": user.email},
            expires_delta=expires,
        )
        return access_token
