import os
import signal
import sys

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
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
    rest_iframe_security,
    rest_token_stats,
)
from ai_server.config.constant import ADMIN_ROLE
from ai_server.exceptions.api_error import ApiError
from ai_server.log.app_logger import AppLogger
from ai_server.log.log_manager import LogManager
from ai_server.log.op_logger import LogCategory, OpLogger
from ai_server.dao.database import db, User
from ai_server.services.rag_svc import RagService
from ai_server.api_controllers.rest_authent import login
from flask_cors import CORS
import pprint

from ai_server.services.user_admin_svc import UserAdminService

logger = AppLogger()
op_logger = OpLogger()


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
                "origins": ["*"],  # URL de votre app Angular
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

    # Define CORS
    main_url_subdirectory = app.config.get("URL_SUBDIRECTORY")

    LogManager().setup_logger(app)
    log_message = f"{app_name} version {app_version} starting..."
    logger.info(log_message)

    op_logger.info(LogCategory.SYSTEM, log_message)

    # Logs some configuration details
    logger.info(f"{app_name} URL main subdirectory is: {main_url_subdirectory}")

    # Setup log exit function
    def end_function():
        #
        #
        # !! Add here process to be performed when application stops !!
        #
        #

        log_message = f"{app_name} version {app_version} stopped!\n"
        logger.warning(log_message)
        op_logger.warning(LogCategory.SYSTEM, log_message)

    def atexit_function(*args):
        log_message = f"{app_name} version {app_version} stop requested (ATEXIT)\n"
        logger.warning(log_message)
        end_function()

    def sigint_function(*args):
        log_message = f"{app_name} version {app_version} stop requested (SIGINT)\n"
        logger.warning(log_message)
        end_function()
        sys.exit(1)

    def sigterm_function(*args):
        log_message = f"{app_name} version {app_version} stop requested (SIGTERM)\n"
        logger.warning(log_message)
        end_function()

    # atexit.register(atexit_function, )
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

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        return render_template("login.html")

    @app.route("/policies", methods=["GET", "POST"])
    def policies():
        return render_template("policies.html")

    @app.route("/terms_of_use")
    def terms_of_use():
        return render_template("terms_of_use.html")

    @app.route("/chat")
    def chat():
        return render_template("chat.html")

    @app.route("/chapters")
    def chapters():
        return render_template("chapters.html")

    @app.route("/logout")
    def logout():
        return redirect(url_for("home"))

    # Setup JWT Manager
    global jwt
    jwt = JWTManager(app)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    with app.app_context():
        app.register_blueprint(rest_authent.bp, url_prefix=main_url_subdirectory)
        app.register_blueprint(rest_rag.bp, url_prefix=main_url_subdirectory)
        app.register_blueprint(rest_knowledge.bp, url_prefix=main_url_subdirectory)
        app.register_blueprint(rest_users_admin.bp, url_prefix=main_url_subdirectory)

        app.register_blueprint(rest_bot.bp, url_prefix=main_url_subdirectory)
        app.register_blueprint(rest_avatar.bp, url_prefix=main_url_subdirectory)

        app.register_blueprint(rest_bot_parameters.bp, url_prefix=main_url_subdirectory)

        app.register_blueprint(rest_bot_assignment.bp, url_prefix=main_url_subdirectory)

        app.register_blueprint(
            rest_iframe_security.bp, url_prefix=main_url_subdirectory
        )

        app.register_blueprint(rest_token_stats.bp, url_prefix=main_url_subdirectory)

        # Define global routing rules
        app.register_error_handler(ApiError, handle_invalid_usage)

        log_message = f"{app_name} version {app_version} started and ready."
        logger.info(log_message)

        db.init_app(app)
        # db.create_all()
        user_admin_svc = UserAdminService()
        super_admin_login = os.getenv("SUPER_ADMIN_LOGIN")
        print(f"SUPER_ADMIN_LOGIN => {super_admin_login}")
        if super_admin_login is not None and not user_admin_svc.get_user_by_email(
            super_admin_login
        ):
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
