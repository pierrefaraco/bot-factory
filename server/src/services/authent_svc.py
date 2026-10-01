from datetime import datetime, timezone
from typing import Optional

from starlette.concurrency import run_in_threadpool

from src.config.config import AppConfig
from src.config.constant import ADMIN_ROLE
from src.models import User
from src.dependencies.auth import issue_access_token
from src.exceptions.service_exceptions import AuthenticationError, NotFoundError
from src.log.bot_factory_logger import BotFactoryLogger
from src.services.base_service import BaseService
from src.services.passwords import hash_password, needs_rehash, verify_password
from src.repositories import RevokedTokenRepository, UserRepository
from src.services.user_admin_svc import UserAdminService


class AuthenticationService(BaseService):
    """Authentication service implementation class"""

    def __init__(
        self,
        user_admin_svc: UserAdminService,
        user_repo: UserRepository,
        revoked_token_repo: RevokedTokenRepository,
    ):
        super().__init__()
        self.logger = BotFactoryLogger()
        self.user_admin_svc = user_admin_svc
        self.user_repo = user_repo
        self.revoked_token_repo = revoked_token_repo

    async def login(self, mail: str, password: str) -> Optional[str]:
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
        self.logger.info(f"Attempting login for user: {mail}")

        user: User = await self.user_repo.get_by_email(mail)
        if not user:
            self.logger.warning(f"Login attempt for non-existent user: {mail}")
            raise NotFoundError("User", mail)

        if not user.is_active:
            msg = f"User {user.name} is not active, administrator can enable it."
            self.logger.warning(msg)
            raise AuthenticationError(msg)

        # CPU-heavy on purpose: off the event loop.
        if not await run_in_threadpool(verify_password, user.password_hash, password):
            self.logger.warning(f"Invalid password for user: {mail}")
            raise AuthenticationError("Invalid credentials")

        # Upgrade hashes written by an older scheme (Werkzeug) to Argon2id.
        if needs_rehash(user.password_hash):
            user.password_hash = await run_in_threadpool(hash_password, password)
            await self.user_repo.commit()

        self.logger.info(f"{mail} (user_id={user.id}) successfully authenticated")

        return self.build_token(user)

    async def login_demo(self) -> str:
        """
        Log into the shared demo account (AppConfig.DEMO_ACCOUNT_EMAIL),
        no password asked: that's the point of the landing page's
        "Try the demo" buttons. What visitors can do with it is limited by
        the account's own role, and by reject_demo_account on the routes
        that change the account itself (users_admin_router.py).

        Raises:
            NotFoundError: demo disabled, or its account doesn't exist
            AuthenticationError: the account is inactive, or an admin
        """
        mail = AppConfig.DEMO_ACCOUNT_EMAIL
        if not mail:
            raise NotFoundError("Demo account", "<disabled>")
        user: User = await self.user_repo.get_by_email(mail)
        if not user:
            raise NotFoundError("Demo account", mail)
        if not user.is_active:
            raise AuthenticationError(f"Demo account {mail} is not active")
        # An admin account behind a password-free public button would hand
        # admin rights to anyone: refuse, whatever the configuration says.
        if ADMIN_ROLE in user.roles:
            raise AuthenticationError(f"Demo account {mail} is an admin account")
        self.logger.info(f"Demo login (user_id={user.id})")
        return self.build_token(user)

    def build_token(self, user: User) -> str:
        return issue_access_token(user.id, user.roles, user.mail)

    async def logout(self, claims: dict) -> None:
        """Revoke the token these claims came from, until its expiry."""
        now = datetime.now(timezone.utc)
        await self.revoked_token_repo.purge_expired(now)
        await self.revoked_token_repo.revoke(
            claims["jti"], datetime.fromtimestamp(claims["exp"], timezone.utc)
        )
        await self.revoked_token_repo.commit()
        self.logger.info(f"Logged out user_id={claims['sub']}")
