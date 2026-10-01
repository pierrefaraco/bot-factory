"""One-time login links: https://<app>/auth?token=<token>.

Lets someone log in with a single click -- e.g. a demo account link sent
to a recruiter -- without ever putting a password in a URL, where it would
end up in nginx access logs, browser history and Referer headers.

The token is 256 random bits, stored only as its SHA-256 (no salt needed:
it's random, not a user-chosen secret), single-use and short-lived, so a
copy left in a log or in the browser history is worthless once redeemed or
expired. Redeeming it only yields the User; AuthenticationService.build_token
turns that into the usual JWT, so the rest of the app can't tell a magic-link
session from a password one.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.exceptions.service_exceptions import AuthenticationError, NotFoundError
from src.log.bot_factory_logger import BotFactoryLogger
from src.models import MagicLink, User
from src.repositories import MagicLinkRepository, UserRepository
from src.services.base_service import BaseService

DEFAULT_TTL_HOURS = 72
MAX_TTL_HOURS = 30 * 24


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class MagicLinkService(BaseService):
    def __init__(self, magic_link_repo: MagicLinkRepository, user_repo: UserRepository):
        super().__init__()
        self.logger = BotFactoryLogger()
        self.magic_link_repo = magic_link_repo
        self.user_repo = user_repo

    async def create(
        self, email: str, ttl_hours: int = DEFAULT_TTL_HOURS
    ) -> tuple[str, datetime]:
        """Creates a link for the account `email`. Returns the clear token --
        the only time it exists anywhere -- and its expiry.

        Raises:
            NotFoundError: no account with this email
            AuthenticationError: the account is deactivated
        """
        user: Optional[User] = await self.user_repo.get_by_email(email)
        if not user:
            raise NotFoundError("User", email)
        if not user.is_active:
            raise AuthenticationError(f"User {user.id} is not active")

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        self.magic_link_repo.add(MagicLink(user.id, _hash_token(token), expires_at))
        await self.magic_link_repo.commit()
        self.logger.info(
            f"Magic link created for user_id={user.id}, expires at {expires_at.isoformat()}"
        )
        return token, expires_at

    async def redeem(self, token: str) -> User:
        """Consumes the link and returns its account.

        Raises:
            AuthenticationError: unknown, expired or already used link, or
            deactivated account -- one error for all, like /auth/login.
        """
        user_id = await self.magic_link_repo.consume(
            _hash_token(token), datetime.now(timezone.utc)
        )
        if user_id is None:
            # Nothing to commit: the UPDATE matched no row.
            raise AuthenticationError("Invalid, expired or already used magic link")

        # Committed before the is_active check on purpose: a link redeemed
        # on a deactivated account is burnt too, not left reusable once the
        # account gets reactivated.
        await self.magic_link_repo.commit()
        user: Optional[User] = await self.user_repo.get(user_id)
        if not user or not user.is_active:
            raise AuthenticationError(f"Magic link redeemed for inactive user {user_id}")

        self.logger.info(f"Magic link redeemed by user_id={user.id}")
        return user
