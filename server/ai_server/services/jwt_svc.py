"""Wrapper for JWT function"""

from flask_jwt_extended import get_jwt_identity
from ai_server.decorators.singleton import singleton


@singleton
class JWTTools:
    """Wrapper main class"""

    @staticmethod
    def get_user():
        """Extract the username from JWT"""
        try:
            identity = get_jwt_identity()
        except RuntimeError:
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
            identity = None

        if isinstance(identity, str) and "|" in identity:
            return identity.split("|")[0]

        return None
