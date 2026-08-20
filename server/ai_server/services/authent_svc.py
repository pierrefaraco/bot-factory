import time
from threading import Thread
import datetime
from typing import Optional

from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity
from werkzeug.security import check_password_hash

from ai_server.dao.database import Bot, User, db
from ai_server.exceptions.service_exceptions import AuthenticationError, NotFoundError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.base_service import BaseService
from ai_server.services.jwt_svc import JWTTools
from ai_server.decorators.singleton import singleton


REVOKED_JWT_LIST = []


@singleton
class AuthenticationService(BaseService):
    """Authentication service implementation class"""

    def __init__(self):
        super().__init__()
        self.logger = BotFactoryLogger()

    def login(self, mail: str, password: str) -> Optional[str]:
        """
        Authenticate user and create access token.

        Args:
            mail: User email address
            password: User password

        Returns:
            Access token if authentication successful, None otherwise

        Raises:
            AuthenticationError: When user is inactive or credentials are invalid
            NotFoundError: When user is not found
        """
        return self._perform_login(
            mail,
            password,
        )

    def _perform_login(self, mail: str, password: str) -> Optional[str]:
        self.logger.info(f"Attempting login for user: {mail}")

        user: User = User.query.filter_by(mail=mail).first()
        if not user:
            self.logger.warning(f"Login attempt for non-existent user: {mail}")
            raise NotFoundError("User", mail)

        if not user.is_active:
            msg = f"User {user.name} is not active, administrator can enable it."
            self.logger.warning(msg)
            raise AuthenticationError(msg)

        if not check_password_hash(user.password_hash, password):
            self.logger.warning(f"Invalid password for user: {mail}")
            raise AuthenticationError("Invalid credentials")

        self.logger.info(f"{mail} (user_id={user.id}) successfully authenticated")

        return self.build_token(user)

    def build_token(self, user):
        expires = datetime.timedelta(minutes=3600)
        access_token = create_access_token(
            identity=f"{user.id}",
            additional_claims={"roles": user.roles, "mail": user.mail},
            expires_delta=expires,
        )
        return access_token

    def logout(self) -> None:
        """
        Logout user by revoking their JWT token.
        """
        user = JWTTools.get_user()
        self.logger.info(f"Logout initiated for user: {user}")
        jti = get_jwt()["jti"]
        self._start_revoke_jti(jti)

    def refresh_token(self) -> str:
        """
        Refresh user JWT token.

        Returns:
            New access token
        """
        jwt = get_jwt()
        self.logger.info(f"Refreshing JWT token for {jwt['sub']}")
        self._start_revoke_jti(jwt["jti"])
        identity = get_jwt_identity()
        access_token = create_access_token(identity=identity)
        self.logger.info(f"JWT token refreshed successfully for user_id={identity}")
        return access_token

    def _start_revoke_jti(self, jti: str) -> None:
        """
        Start asynchronous JWT token revocation.

        Args:
            jti: JWT ID to revoke
        """
        thread = Thread(target=self._revoke_jti, args=(jti, "new_jwt"))
        thread.setDaemon(True)
        thread.start()

    def _revoke_jti(self, jti: str, new_jwt: str) -> None:
        """
        Revoke JWT token after delay.

        Args:
            jti: JWT ID to revoke
            new_jwt: New JWT token identifier
        """
        self.logger.debug(f"JWT {jti} will be revoked in 20 seconds")
        time.sleep(20)
        global REVOKED_JWT_LIST
        REVOKED_JWT_LIST.append(jti)
        self.logger.debug(f"JWT {jti} has been revoked")

    def is_jwt_revoked(self) -> bool:
        """
        Check if current JWT token is revoked.

        Returns:
            True if token is revoked, False otherwise
        """
        jti = get_jwt()["jti"]
        global REVOKED_JWT_LIST
        self.logger.debug(f"Checking if JWT {jti} is in revoked list")
        return jti in REVOKED_JWT_LIST
