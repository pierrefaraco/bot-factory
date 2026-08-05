"""
Validator pour la configuration de l'application
Vérifie que toutes les variables d'environnement critiques sont configurées
"""

from ai_server.log.app_logger import AppLogger

logger = AppLogger()


class ConfigValidator:
    """Validateur de configuration pour s'assurer que l'application est correctement configurée"""

    @staticmethod
    def validate_jwt_config(config) -> None:
        """
        Valide la configuration JWT

        Args:
            config: L'objet de configuration Flask

        Raises:
            ValueError: Si la configuration JWT n'est pas valide
        """
        errors = []

        # Vérifier que le JWT secret n'est pas la valeur par défaut
        if not config.JWT_SECRET_KEY:
            errors.append("JWT_SECRET_KEY is not configured")

        # Vérifier que la clé JWT fait au moins 32 caractères
        if config.JWT_SECRET_KEY and len(config.JWT_SECRET_KEY) < 32:
            errors.append("JWT_SECRET_KEY should be at least 32 characters long")

        # Avertissement si la clé contient des caractères peu sécurisés
        if (
            config.JWT_SECRET_KEY
            and config.JWT_SECRET_KEY
            == '^ZQjGKyBVf2xZQjGKyBVf2xZQjGKyBVf2xZQjGKyBVf2x")sZQjGKyBVf2xx'
        ):
            errors.append(
                "JWT_SECRET_KEY is using the default hardcoded value - CHANGE THIS IN PRODUCTION!"
            )

        if errors:
            error_message = "JWT configuration validation failed:\n" + "\n".join(
                f"  - {err}" for err in errors
            )
            logger.error(error_message)
            raise ValueError(error_message)

        logger.info("JWT configuration validated successfully")

    @staticmethod
    def validate_database_config(config) -> None:
        """
        Valide la configuration de la base de données

        Args:
            config: L'objet de configuration Flask

        Raises:
            ValueError: Si la configuration de la base de données n'est pas valide
        """
        errors = []

        if not config.DATABASE_URL:
            errors.append("DATABASE_URL environment variable is not configured")

        if errors:
            error_message = "Database configuration validation failed:\n" + "\n".join(
                f"  - {err}" for err in errors
            )
            logger.error(error_message)
            raise ValueError(error_message)

        logger.info("Database configuration validated successfully")

    @staticmethod
    def validate_all(config, strict_mode: bool = True) -> bool:
        """
        Valide toute la configuration de l'application

        Args:
            config: L'objet de configuration Flask
            strict_mode: Si True, lève une exception en cas d'erreur. Si False, log seulement les avertissements

        Returns:
            bool: True si la validation réussit

        Raises:
            ValueError: Si strict_mode est True et que la validation échoue
        """
        logger.info("Starting configuration validation...")

        try:
            ConfigValidator.validate_database_config(config)
            ConfigValidator.validate_jwt_config(config)

            logger.info("All configuration validation checks passed")
            return True

        except ValueError as e:
            if strict_mode:
                logger.critical(
                    f"Configuration validation failed in strict mode: {str(e)}"
                )
                raise
            else:
                logger.warning(
                    f"Configuration validation failed (non-strict mode): {str(e)}"
                )
                return False
