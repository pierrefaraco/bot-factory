"""Wrapper for JWT function"""

from ai_server.decorators.singleton import singleton


@singleton
class JWTTools:
    """Wrapper main class"""

    @staticmethod
    def get_user():
        """Extract the username from JWT"""
        # identity is a plain user id string (see authent_svc.build_token),
        # never "app|user" -- the split below never actually matched, on
        # Flask-JWT-Extended or since. Kept returning the same "SYSTEM"
        # fallback callers already got either way.
        return "SYSTEM"

    @staticmethod
    def get_app_name():
        """Extract the application name from JWT"""
        return None
