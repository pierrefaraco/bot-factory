"""Token Statistics REST API Controller"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, get_jwt
from http import HTTPStatus
from pydantic import BaseModel, Field

from ai_server.config.openapi import api
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.token_tracking_svc import TokenTrackingService
from ai_server.decorators.role_required import role_required
from ai_server.decorators.user_scope import authorize_user_scope
from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE

CONTROLLER_NAME = "token_stats"
CONTROLLER_PATH = "/token-stats"

bp = Blueprint(CONTROLLER_NAME, __name__)


class TokenHistoryQuery(BaseModel):
    """Query parameters for token usage history"""

    limit: int = Field(default=100, ge=1, le=1000)
    last24h: bool = False


# Services initialization
logger = BotFactoryLogger()
token_tracking_svc = TokenTrackingService()


@bp.route(f"{CONTROLLER_PATH}/me", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["token-stats"], security={"BearerAuth": []})
def get_token_stats_self():
    """Get token statistics for the current user"""
    try:
        user_id = get_jwt_identity()
        stats = token_tracking_svc.get_user_token_stats(user_id)
        return jsonify(stats), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user token stats: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/user/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["token-stats"], security={"BearerAuth": []})
def get_token_stats_by_id(user_id):
    """Get token statistics for a user (own guest, or any user if admin)"""
    try:
        error = authorize_user_scope(user_id)
        if error:
            return error
        stats = token_tracking_svc.get_user_token_stats(user_id)
        return jsonify(stats), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user token stats: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/history/me", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(query=TokenHistoryQuery, tags=["token-stats"], security={"BearerAuth": []})
def get_token_history_self():
    """Get token usage history for the current user"""
    try:
        user_id = get_jwt_identity()
        limit = request.args.get("limit", default=100, type=int)
        last_24h = (
            request.args.get("last24h", default="false", type=str).lower() == "true"
        )
        if limit < 1 or limit > 1000:
            return jsonify(
                {"error": "Limit must be between 1 and 1000"}
            ), HTTPStatus.BAD_REQUEST

        history = token_tracking_svc.get_user_token_history(user_id, limit, last_24h)
        return jsonify({"history": history}), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user token history: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/history/user/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(query=TokenHistoryQuery, tags=["token-stats"], security={"BearerAuth": []})
def get_token_history_by_id(user_id):
    """Get token usage history for a user (own guest, or any user if admin)"""
    try:
        error = authorize_user_scope(user_id)
        if error:
            return error

        limit = request.args.get("limit", default=100, type=int)
        last_24h = request.args.get("last24h", default=False, type=bool)
        if limit < 1 or limit > 1000:
            return jsonify(
                {"error": "Limit must be between 1 and 1000"}
            ), HTTPStatus.BAD_REQUEST

        history = token_tracking_svc.get_user_token_history(user_id, limit, last_24h)
        return jsonify({"history": history}), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user token history: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/bot/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["token-stats"], security={"BearerAuth": []})
def get_bot_token_stats(bot_id):
    """Get token statistics for a specific bot"""
    try:
        stats = token_tracking_svc.get_bot_token_stats(bot_id)
        return jsonify(stats), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting bot token stats: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/all-users", methods=["GET"])
@role_required([ADMIN_ROLE])
@api.validate(tags=["token-stats"], security={"BearerAuth": []})
def get_all_users_token_stats():
    """Get token statistics for all users (admin only)"""
    try:
        stats = token_tracking_svc.get_all_users_token_stats()
        return jsonify({"users": stats}), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting all users token stats: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/total/me", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["token-stats"], security={"BearerAuth": []})
def get_total_tokens_self():
    """Get total tokens consumed by the current user"""
    try:
        user_id = get_jwt_identity()
        total = token_tracking_svc.get_user_total_tokens(user_id)
        return jsonify({"user_id": user_id, "total_tokens": total}), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user total tokens: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/total/user/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["token-stats"], security={"BearerAuth": []})
def get_total_tokens_by_id(user_id):
    """Get total tokens consumed by a user (own guest, or any user if admin)"""
    try:
        error = authorize_user_scope(user_id)
        if error:
            return error
        total = token_tracking_svc.get_user_total_tokens(user_id)
        return jsonify({"user_id": user_id, "total_tokens": total}), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user total tokens: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/last-24h/me", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["token-stats"], security={"BearerAuth": []})
def get_tokens_last_24h_self():
    """Get total tokens consumed by the current user in the last 24 hours"""
    try:
        user_id = get_jwt_identity()
        total = token_tracking_svc.get_user_tokens_last_24h(user_id)
        return jsonify(
            {"user_id": user_id, "total_tokens_last_24h": total}
        ), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user tokens last 24h: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/last-24h/user/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["token-stats"], security={"BearerAuth": []})
def get_tokens_last_24h_by_id(user_id):
    """Get total tokens consumed by a user in the last 24h (own guest, or
    any user if admin)"""
    try:
        error = authorize_user_scope(user_id)
        if error:
            return error
        total = token_tracking_svc.get_user_tokens_last_24h(user_id)
        return jsonify(
            {"user_id": user_id, "total_tokens_last_24h": total}
        ), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user tokens last 24h: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/stats-24h/me", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["token-stats"], security={"BearerAuth": []})
def get_stats_last_24h_self():
    """Get detailed token statistics for the current user in the last 24 hours"""
    try:
        user_id = get_jwt_identity()
        stats = token_tracking_svc.get_user_stats_last_24h(user_id)
        return jsonify(stats), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user stats last 24h: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/stats-24h/user/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["token-stats"], security={"BearerAuth": []})
def get_stats_last_24h_by_id(user_id):
    """Get detailed token stats for a user in the last 24h (own guest, or
    any user if admin)"""
    try:
        error = authorize_user_scope(user_id)
        if error:
            return error
        stats = token_tracking_svc.get_user_stats_last_24h(user_id)
        return jsonify(stats), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user stats last 24h: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/admin-summary", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["token-stats"], security={"BearerAuth": []})
def get_admin_token_usage_summary():
    """Get 24h/30d token totals for every account and guest the caller can
    see in one batch call (for the admin Guest/User tables) -- everyone for
    Admin, only the caller's own account + guests for a User (a guest's
    usage is always recorded under its parent's user_id, so scoping by
    user_id already covers both)."""
    try:
        caller_id = get_jwt_identity()
        roles = get_jwt().get("roles", [])
        scope_user_id = None if ADMIN_ROLE in roles else int(caller_id)
        summary = token_tracking_svc.get_admin_token_usage_summary(scope_user_id)
        return jsonify(summary), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting admin token usage summary: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
