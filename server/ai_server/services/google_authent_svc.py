import datetime
from multiprocessing import AuthenticationError
from ai_server.services.base_service import BaseService
from google.oauth2 import id_token
from google.auth.transport import requests
from ai_server.dependencies.auth import create_access_token
from ai_server.services.user_admin_svc import UserAdminService
from ai_server.dao.database import User
from ai_server.dto.user_dto import UserDto
from ai_server.decorators.singleton import singleton

CLIENT_ID = "913568537440-clfeb4jvitdh7111s1j8cv6u8gb6t3dv.apps.googleusercontent.com"


@singleton
class GoogleAuthentSvc(BaseService):
    """Service for handling Google OAuth operations"""

    def __init__(self):
        super().__init__()
        self.user_admin_svc = UserAdminService()

    def verify_google_token(self, credential):
        try:
            id_info = id_token.verify_oauth2_token(
                credential, requests.Request(), CLIENT_ID
            )
            # Never log the full id_info payload: it carries PII (name,
            # picture, locale...) beyond what's needed for the audit trail.
            self.logger.info(f"Google OAuth token verified for email={id_info['email']}")

            user: User = User.query.filter_by(mail=id_info["email"]).first()

            if not user:
                user_dto = self.record_user(id_info)
            else:
                user_dto = self.user_admin_svc.user_to_dto(user)
            if not user_dto.is_active:
                msg = f"User {user.name} is not active, administrator can enable it."
                self.logger.warning(msg)
                raise AuthenticationError(msg)

            self.logger.info(f"Google OAuth login succeeded for user_id={user_dto.id}")
            return self.build_token(user_dto)
        except ValueError as e:
            # Expected validation failure (invalid/expired Google token), not
            # a system error, and never log the credential/token value itself.
            self.logger.warning(f"Invalid Google OAuth token: {e}")
            return None

    def record_user(self, id_info: dict) -> UserDto:
        self.logger.info(f"Auto-provisioning new user from Google OAuth: email={id_info['email']}")
        return self.user_admin_svc.register_new_user(
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
