"""Startup checks on the security-critical configuration: the API refuses
to start (see asgi.py's lifespan) rather than run with a guessable secret."""

from src.log.bot_factory_logger import BotFactoryLogger

logger = BotFactoryLogger()

JWT_SECRET_MIN_LENGTH = 32
SUPER_ADMIN_PASSWORD_MIN_LENGTH = 12

# Values that have been published in this repository (.env.example files,
# README, former defaults): anyone can sign tokens with them, whatever
# their length. test_config_validator_unit.py checks that the .env.example
# files' own values stay listed here.
KNOWN_PLACEHOLDER_SECRETS = frozenset(
    {
        "your-secret-key-change-in-production",
        "your-secret-key-change-this-in-production",
        '^ZQjGKyBVf2xZQjGKyBVf2xZQjGKyBVf2xZQjGKyBVf2x")sZQjGKyBVf2xx',
        "change-me",
        "123",
    }
)


class ConfigValidator:
    """Raises ValueError, listing every problem found, on unsafe settings."""

    @staticmethod
    def jwt_errors(secret: str) -> list:
        if not secret:
            return ["JWT_SECRET_KEY is not set"]
        if secret in KNOWN_PLACEHOLDER_SECRETS:
            return ["JWT_SECRET_KEY is a published placeholder value"]
        if len(secret) < JWT_SECRET_MIN_LENGTH:
            return [f"JWT_SECRET_KEY must be at least {JWT_SECRET_MIN_LENGTH} characters"]
        return []

    @staticmethod
    def super_admin_password_errors(password: str) -> list:
        """Only checked when the super admin account gets created: the
        variable is unused once it exists."""
        if not password:
            return ["SUPER_ADMIN_PASSWORD is not set"]
        if password in KNOWN_PLACEHOLDER_SECRETS:
            return ["SUPER_ADMIN_PASSWORD is a published placeholder value"]
        if len(password) < SUPER_ADMIN_PASSWORD_MIN_LENGTH:
            return [
                f"SUPER_ADMIN_PASSWORD must be at least "
                f"{SUPER_ADMIN_PASSWORD_MIN_LENGTH} characters"
            ]
        return []

    @staticmethod
    def raise_if_any(errors: list) -> None:
        if errors:
            message = "Unsafe configuration:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.critical(message)
            raise ValueError(message)

    @staticmethod
    def validate_all(config) -> None:
        errors = ConfigValidator.jwt_errors(config.JWT_SECRET_KEY)
        if not config.DATABASE_URL:
            errors.append("DATABASE_URL is not set")
        ConfigValidator.raise_if_any(errors)
