"""Wrapper for JWT function"""

from flask_jwt_extended import get_jwt_identity
from ai_server.decorators.singleton import singleton
from ai_server.log.bot_factory_logger import BotFactoryLogger

logger = BotFactoryLogger()


@singleton
class JWTTools:
    """Wrapper main class"""

    @staticmethod
    def get_user():
        """Extract the username from JWT"""
        try:
            identity = get_jwt_identity()
        except RuntimeError:
            # Called outside a request/JWT context (e.g. background thread) -
            # expected fallback, not an error, hence debug rather than warning.
            logger.debug("get_user() called outside JWT context, falling back to SYSTEM")
            identity = None

        if isinstance(identity, str) and "|" in identity:
            return identity.split("|")[1]

        return "SYSTEM"

    @staticmethod
    def get_app_name():
        """Extract the application name from JWT"""

        try:
            identity = get_jwt_identity()
        except RuntimeError:
            logger.debug("get_app_name() called outside JWT context, falling back to None")
            identity = None

        if isinstance(identity, str) and "|" in identity:
            return identity.split("|")[0]

        return None
