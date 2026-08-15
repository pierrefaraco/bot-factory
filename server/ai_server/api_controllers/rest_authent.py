"""Authentication REST API Controller"""

from flask import Blueprint, jsonify, make_response, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from http import HTTPStatus
from pydantic import BaseModel, EmailStr, Field, ValidationError

from ai_server.config.openapi import api, pydantic_error_messages
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.authent_svc import AuthenticationService
from ai_server.dao.database import db, User
from ai_server.services.google_authent_svc import GoogleAuthentSvc

CONTROLLER_NAME = "authent"
CONTROLLER_PATH = "/auth"

bp = Blueprint(CONTROLLER_NAME, __name__)


class GoogleOAuthRequest(BaseModel):
    """Schema for Google OAuth login validation"""

    credential: str = Field(min_length=1)


class LoginRequest(BaseModel):
    """Schema for login validation"""

    email: EmailStr
    password: str = Field(min_length=1)


# Services initialization
app_logger = BotFactoryLogger()
auth_svc = AuthenticationService()
google_auth_svc = GoogleAuthentSvc()


@bp.route(f"{CONTROLLER_PATH}/login", methods=["POST"])
@api.validate(json=LoginRequest, tags=["auth"])
def login():
    """User login with email and password. Returns a JWT access token."""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = LoginRequest.model_validate(data).model_dump()

        app_logger.info(f"User attempting login with email: {validated_data['email']}")

        access_token = auth_svc.login(
            validated_data["email"], validated_data["password"]
        )
        if access_token is None:
            app_logger.warning(
                f"Failed login attempt for email: {validated_data['email']}"
            )
            return jsonify(
                {"error": "Invalid email or password"}
            ), HTTPStatus.UNAUTHORIZED

        app_logger.info(f"Successful login for email: {validated_data['email']}")
        return jsonify({"token": access_token}), HTTPStatus.OK

    except ValidationError as e:
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        app_logger.error(f"Login error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/google", methods=["POST"])
@api.validate(json=GoogleOAuthRequest, tags=["auth"])
def login_with_google():
    """User login with a Google OAuth credential. Returns a JWT access token."""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = GoogleOAuthRequest.model_validate(data).model_dump()

        app_logger.info(
            f"User attempting login with credential: {validated_data['credential']}"
        )

        access_token = google_auth_svc.verify_google_token(validated_data["credential"])
        if access_token is None:
            app_logger.warning(
                f"Failed login attempt for credential: {validated_data['credential']}"
            )
            return jsonify(
                {"error": "Invalid email or password"}
            ), HTTPStatus.UNAUTHORIZED
        app_logger.info(
            f"Successful login for credential: {validated_data['credential']}"
        )
        return jsonify({"token": access_token}), HTTPStatus.OK
    except ValidationError as e:
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        app_logger.error(f"Login error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/refresh", methods=["POST"])
@jwt_required()
@api.validate(tags=["auth"], security={"BearerAuth": []})
def refresh():
    """Refresh JWT access token"""
    try:
        access_token = auth_svc.refresh_token()
        return jsonify({"access_token": access_token}), HTTPStatus.OK
    except Exception as exc:
        app_logger.error(f"Token refresh error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/logout", methods=["POST"])
@jwt_required()
@api.validate(tags=["auth"], security={"BearerAuth": []})
def logout():
    """User logout"""
    try:
        user_id = get_jwt_identity()
        app_logger.info(f"User {user_id} logging out")

        auth_svc.logout()
        app_logger.info(f"User {user_id} logged out successfully")

        return jsonify({"message": "Logged out successfully"}), HTTPStatus.OK

    except Exception as exc:
        app_logger.error(f"Logout error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.before_request
def handle_json():
    """Ensure JSON content type for POST requests"""
    if request.method == "POST" and not request.is_json:
        return jsonify(
            {"error": "Content-Type must be application/json"}
        ), HTTPStatus.BAD_REQUEST
