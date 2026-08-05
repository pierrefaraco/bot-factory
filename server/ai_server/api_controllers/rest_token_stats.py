"""Token Statistics REST API Controller"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.token_tracking_svc import TokenTrackingService
from ai_server.decorators.role_required import role_required
from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dao.database import User

CONTROLLER_NAME = "token_stats"
CONTROLLER_PATH = "/token-stats"

bp = Blueprint(CONTROLLER_NAME, __name__)

# Services initialization
logger = BotFactoryLogger()
token_tracking_svc = TokenTrackingService()


@bp.route(f"{CONTROLLER_PATH}/self", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
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


@bp.route(f"{CONTROLLER_PATH}/guest/<int:guest_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
def get_token_stats_guest(guest_id):
    """Get token statistics for a guest user"""
    try:
        user_id = get_jwt_identity()
        guest = User.query.filter_by(id=guest_id).first()

        if not guest:
            return jsonify({"error": "Guest user not found"}), HTTPStatus.NOT_FOUND

        if guest.parent_id != int(user_id):
            return jsonify(
                {
                    "error": f"Unable to access stats for user {guest_id} - not your guest"
                }
            ), HTTPStatus.FORBIDDEN

        stats = token_tracking_svc.get_user_token_stats(guest_id)
        return jsonify(stats), HTTPStatus.OK

    except Exception as exc:
        logger.error(f"Error getting guest token stats: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/user/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE])
def get_token_stats_user(user_id):
    """Get token statistics for a specific user (admin only)"""
    try:
        stats = token_tracking_svc.get_user_token_stats(user_id)
        return jsonify(stats), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user token stats: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/history/self", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
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


@bp.route(f"{CONTROLLER_PATH}/history/guest/<int:guest_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
def get_token_history_guest(guest_id):
    """Get token usage history for a guest user"""
    try:
        user_id = get_jwt_identity()
        guest = User.query.filter_by(id=guest_id).first()

        if not guest:
            return jsonify({"error": "Guest user not found"}), HTTPStatus.NOT_FOUND

        if guest.parent_id != int(user_id):
            return jsonify(
                {
                    "error": f"Unable to access history for user {guest_id} - not your guest"
                }
            ), HTTPStatus.FORBIDDEN

        limit = request.args.get("limit", default=100, type=int)
        last_24h = request.args.get("last24h", default=False, type=bool)
        if limit < 1 or limit > 1000:
            return jsonify(
                {"error": "Limit must be between 1 and 1000"}
            ), HTTPStatus.BAD_REQUEST

        history = token_tracking_svc.get_user_token_history(guest_id, limit, last_24h)
        return jsonify({"history": history}), HTTPStatus.OK

    except Exception as exc:
        logger.error(f"Error getting guest token history: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/history/user/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE])
def get_token_history_user(user_id):
    """Get token usage history for a specific user (admin only)"""
    try:
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


@bp.route(f"{CONTROLLER_PATH}/total/self", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
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


@bp.route(f"{CONTROLLER_PATH}/total/guest/<int:guest_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
def get_total_tokens_guest(guest_id):
    """Get total tokens consumed by a guest user"""
    try:
        user_id = get_jwt_identity()
        guest = User.query.filter_by(id=guest_id).first()

        if not guest:
            return jsonify({"error": "Guest user not found"}), HTTPStatus.NOT_FOUND

        if guest.parent_id != int(user_id):
            return jsonify(
                {
                    "error": f"Unable to access tokens for user {guest_id} - not your guest"
                }
            ), HTTPStatus.FORBIDDEN

        total = token_tracking_svc.get_user_total_tokens(guest_id)
        return jsonify({"user_id": guest_id, "total_tokens": total}), HTTPStatus.OK

    except Exception as exc:
        logger.error(f"Error getting guest total tokens: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/total/user/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE])
def get_total_tokens_user(user_id):
    """Get total tokens consumed by a specific user (admin only)"""
    try:
        total = token_tracking_svc.get_user_total_tokens(user_id)
        return jsonify({"user_id": user_id, "total_tokens": total}), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user total tokens: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/last-24h/self", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
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


@bp.route(f"{CONTROLLER_PATH}/last-24h/guest/<int:guest_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
def get_tokens_last_24h_guest(guest_id):
    """Get total tokens consumed by a guest user in the last 24 hours"""
    try:
        user_id = get_jwt_identity()
        guest = User.query.filter_by(id=guest_id).first()

        if not guest:
            return jsonify({"error": "Guest user not found"}), HTTPStatus.NOT_FOUND

        if guest.parent_id != int(user_id):
            return jsonify(
                {
                    "error": f"Unable to access tokens for user {guest_id} - not your guest"
                }
            ), HTTPStatus.FORBIDDEN

        total = token_tracking_svc.get_user_tokens_last_24h(guest_id)
        return jsonify(
            {"user_id": guest_id, "total_tokens_last_24h": total}
        ), HTTPStatus.OK

    except Exception as exc:
        logger.error(f"Error getting guest tokens last 24h: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/last-24h/user/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE])
def get_tokens_last_24h_user(user_id):
    """Get total tokens consumed by a specific user in the last 24 hours (admin only)"""
    try:
        total = token_tracking_svc.get_user_tokens_last_24h(user_id)
        return jsonify(
            {"user_id": user_id, "total_tokens_last_24h": total}
        ), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user tokens last 24h: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/stats-24h/self", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
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


@bp.route(f"{CONTROLLER_PATH}/stats-24h/guest/<int:guest_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
def get_stats_last_24h_guest(guest_id):
    """Get detailed token statistics for a guest user in the last 24 hours"""
    try:
        user_id = get_jwt_identity()
        guest = User.query.filter_by(id=guest_id).first()

        if not guest:
            return jsonify({"error": "Guest user not found"}), HTTPStatus.NOT_FOUND

        if guest.parent_id != int(user_id):
            return jsonify(
                {
                    "error": f"Unable to access stats for user {guest_id} - not your guest"
                }
            ), HTTPStatus.FORBIDDEN

        stats = token_tracking_svc.get_user_stats_last_24h(guest_id)
        return jsonify(stats), HTTPStatus.OK

    except Exception as exc:
        logger.error(f"Error getting guest stats last 24h: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/stats-24h/user/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE])
def get_stats_last_24h_user(user_id):
    """Get detailed token statistics for a specific user in the last 24 hours (admin only)"""
    try:
        stats = token_tracking_svc.get_user_stats_last_24h(user_id)
        return jsonify(stats), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error getting user stats last 24h: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
