import os
import signal
import sys

from flask import Flask, jsonify
from flask.wrappers import Response
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from ai_server.api_controllers import (
    rest_authent,
    rest_bot,
    rest_bot_assignment,
    rest_knowledge,
    rest_rag,
    rest_users_admin,
    rest_avatar,
    rest_bot_parameters,
    rest_token_stats,
)
from ai_server.config.constant import ADMIN_ROLE
from ai_server.config.openapi import api as openapi
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.log.log_manager import LogManager
from ai_server.dao.database import db
from ai_server.services.user_admin_svc import UserAdminService

logger = BotFactoryLogger()


def handle_invalid_usage(error) -> Response:
    """Generic handler for invalid URL usage"""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def create_app():
    """Create and configure an instance of the Flask application."""

    # Create HTTP application (app)
    app = Flask(__name__, instance_relative_config=True)

    # CORS configuration
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": ["*"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": [
                    "Content-Type",
                    "X-Frame-Token",
                    "X-CSRF-Token",
                    "Authorization",
                ],
                "supports_credentials": True,
            }
        },
    )

    # Apply configuration
    app.config.from_object("ai_server.config.config.AppConfig")
    app_name = app.config.get("APP_NAME")
    app_version = app.config.get("APP_VERSION")
    main_url_subdirectory = app.config.get("URL_SUBDIRECTORY")

    LogManager().setup_logger(app)
    logger.info(f"{app_name} version {app_version} starting...")
    logger.info(f"{app_name} URL main subdirectory is: {main_url_subdirectory}")

    def stop_requested(reason):
        logger.warning(f"{app_name} version {app_version} stop requested ({reason})\n")
        logger.warning(f"{app_name} version {app_version} stopped!\n")

    def sigint_function(*args):
        stop_requested("SIGINT")
        sys.exit(1)

    def sigterm_function(*args):
        stop_requested("SIGTERM")

    if not sys.platform.startswith("linux"):
        signal.signal(signal.SIGINT, sigint_function)
    signal.signal(signal.SIGTERM, sigterm_function)

    @app.after_request
    def after_request(response):
        response.headers.add(
            "Access-Control-Allow-Headers",
            "X-Requested-With, Content-Type,  Authorization, Accept, Client-Security-Token, Accept-Encoding, X-Auth-Token",
        )
        return response

    # Setup JWT Manager
    JWTManager(app)

    # ensure the instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    with app.app_context():
        blueprints = (
            rest_authent.bp,
            rest_rag.bp,
            rest_knowledge.bp,
            rest_users_admin.bp,
            rest_bot.bp,
            rest_avatar.bp,
            rest_bot_parameters.bp,
            rest_bot_assignment.bp,
            rest_token_stats.bp,
        )
        for bp in blueprints:
            app.register_blueprint(bp, url_prefix=main_url_subdirectory)

        # Define global routing rules
        app.register_error_handler(ApiError, handle_invalid_usage)

        @app.route(f"{main_url_subdirectory}/health")
        def health_check() -> Response:
            return jsonify({"status": "ok"})

        # OpenAPI documentation (SpecTree): Swagger UI at /api/docs/swagger/
        openapi.register(app)

        logger.info(f"{app_name} version {app_version} started and ready.")

        db.init_app(app)

        user_admin_svc = UserAdminService()
        super_admin_login = os.getenv("SUPER_ADMIN_LOGIN")
        if super_admin_login and not user_admin_svc.get_user_by_email(super_admin_login):
            logger.info(f"Creating super admin user: {super_admin_login}")
            user_admin_svc.register_user(
                mail=super_admin_login,
                user_name=super_admin_login,
                password=os.getenv("SUPER_ADMIN_PASSWORD"),
                roles=ADMIN_ROLE,
                parent_id=-1,
                is_active=True,
            )

        return app


# Create the app instance
app = create_app()
