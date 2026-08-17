"""Bot Guest Assignment REST API Controller"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from pydantic import BaseModel, ValidationError

from ai_server.config.openapi import api, pydantic_error_messages

from ai_server.dao.database import User
from ai_server.dto.bot_assignment_dto import BotAssignmentDto
from ai_server.services.bot_assignment_svc import BotAssignmentService
from ai_server.config.constant import USER_ROLE, ADMIN_ROLE, GUEST_ROLE
from ai_server.decorators.role_required import role_required
from ai_server.log.bot_factory_logger import BotFactoryLogger

CONTROLLER_NAME = "bot-guest-assignment"
CONTROLLER_PATH = "/bot-guest-assignment"

bp = Blueprint(CONTROLLER_NAME, __name__)


class BotGuestAssignmentRequest(BaseModel):
    """Schema for bot guest assignment validation"""

    bot_id: int
    guest_user_id: int
    is_active: bool = True


class BotGuestAssignmentUpdateRequest(BaseModel):
    """Schema for updating bot guest assignment"""

    is_active: bool


class BotGuestAssignmentRefRequest(BaseModel):
    """Schema referencing an assignment by bot and guest user"""

    bot_id: int
    guest_user_id: int


# Services initialization
bot_assignment_svc = BotAssignmentService()
logger = BotFactoryLogger()


@bp.route(CONTROLLER_PATH, methods=["POST"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=BotGuestAssignmentRequest, tags=["bot-assignment"], security={"BearerAuth": []})
def create_assignment():
    """Create a new bot guest assignment"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = BotGuestAssignmentRequest.model_validate(data).model_dump()

        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        # Add the assigner information; the service expects "user_id" for
        # the assignee (the DTO field is named guest_user_id for API clarity).
        validated_data["assigned_by"] = user_id
        validated_data["user_id"] = validated_data["guest_user_id"]

        assignment_dto = bot_assignment_svc.create(validated_data)
        if assignment_dto:
            return jsonify(assignment_dto.to_dict()), HTTPStatus.CREATED

        return jsonify(
            {"error": "Failed to create assignment"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR

    except ValidationError as e:
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Assignment creation error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/parent/<int:parent_user_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["bot-assignment"], security={"BearerAuth": []})
def get_assignments_by_parent(parent_user_id):
    """Get all assignments created by a parent user"""
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        # Users can only see their own assignments (unless they're admin)
        if user.roles != ADMIN_ROLE and int(user_id) != parent_user_id:
            return jsonify({"error": "Forbidden"}), HTTPStatus.FORBIDDEN

        assignments = bot_assignment_svc.get_assignments_by_parent(parent_user_id)
        return jsonify(
            [assignment.to_dict() for assignment in assignments]
        ), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Get assignments by parent error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/guest/<int:guest_user_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["bot-assignment"], security={"BearerAuth": []})
def get_assignments_by_guest(guest_user_id):
    """Get all assignments for a guest user"""
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        # Users can only see assignments for their own guests, or guests can see their own assignments
        if user.roles == GUEST_ROLE:
            if int(user_id) != guest_user_id:
                return jsonify({"error": "Forbidden"}), HTTPStatus.FORBIDDEN
        elif user.roles in [USER_ROLE, ADMIN_ROLE]:
            guest_user: User = User.query.filter_by(id=guest_user_id).first()
            if not guest_user or (
                user.roles != ADMIN_ROLE and guest_user.parent_id != int(user_id)
            ):
                return jsonify({"error": "Forbidden"}), HTTPStatus.FORBIDDEN

        assignments = bot_assignment_svc.get_assignments_by_user(guest_user_id)
        return jsonify(
            [assignment.to_dict() for assignment in assignments]
        ), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Get assignments by guest error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/guest/<int:guest_user_id>/bot-ids", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["bot-assignment"], security={"BearerAuth": []})
def get_assigned_bot_ids(guest_user_id):
    """Get list of bot IDs assigned to a guest user"""
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        # Same authorization logic as above
        if user.roles == GUEST_ROLE:
            if int(user_id) != guest_user_id:
                return jsonify({"error": "Forbidden"}), HTTPStatus.FORBIDDEN
        elif user.roles in [USER_ROLE, ADMIN_ROLE]:
            guest_user: User = User.query.filter_by(id=guest_user_id).first()
            if not guest_user or (
                user.roles != ADMIN_ROLE and guest_user.parent_id != int(user_id)
            ):
                return jsonify({"error": "Forbidden"}), HTTPStatus.FORBIDDEN

        bot_ids = bot_assignment_svc.get_assigned_bot_ids_for_user(guest_user_id)
        return jsonify({"bot_ids": bot_ids}), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Get assigned bot IDs error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:assignment_id>", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=BotGuestAssignmentUpdateRequest, tags=["bot-assignment"], security={"BearerAuth": []})
def update_assignment(assignment_id):
    """Update a bot guest assignment"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = BotGuestAssignmentUpdateRequest.model_validate(data).model_dump()

        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        # Get the assignment to check ownership
        assignment = bot_assignment_svc.get_dto_by_id(assignment_id)
        if not assignment:
            return jsonify({"error": "Assignment not found"}), HTTPStatus.NOT_FOUND
        if user.roles != ADMIN_ROLE and assignment.assigned_by != int(user_id):
            return jsonify({"error": "Forbidden"}), HTTPStatus.FORBIDDEN

        updated_assignment = bot_assignment_svc.update(assignment_id, validated_data)
        return jsonify(updated_assignment.to_dict()), HTTPStatus.OK

    except ValidationError as e:
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Assignment update error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:assignment_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["bot-assignment"], security={"BearerAuth": []})
def delete_assignment(assignment_id):
    """Delete a bot guest assignment"""
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        # Get the assignment to check ownership
        assignment = bot_assignment_svc.get_dto_by_id(assignment_id)
        if not assignment:
            return jsonify({"error": "Assignment not found"}), HTTPStatus.NOT_FOUND
        if user.roles != ADMIN_ROLE and assignment.assigned_by != int(user_id):
            return jsonify({"error": "Forbidden"}), HTTPStatus.FORBIDDEN

        success = bot_assignment_svc.delete(assignment_id)
        if not success:
            return jsonify({"error": "Assignment not found"}), HTTPStatus.NOT_FOUND

        return "", HTTPStatus.NO_CONTENT

    except Exception as e:
        logger.error(f"Assignment deletion error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/remove", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=BotGuestAssignmentRefRequest, tags=["bot-assignment"], security={"BearerAuth": []})
def remove_assignment():
    """Remove assignment between a bot and guest user"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        if "bot_id" not in data or "guest_user_id" not in data:
            return jsonify(
                {"error": "bot_id and guest_user_id are required"}
            ), HTTPStatus.BAD_REQUEST

        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        success = bot_assignment_svc.remove_assignment(
            data["bot_id"], data["guest_user_id"]
        )
        if not success:
            return jsonify({"error": "Assignment not found"}), HTTPStatus.NOT_FOUND

        return jsonify({"message": "Assignment removed successfully"}), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Assignment removal error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/check", methods=["POST"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(json=BotGuestAssignmentRefRequest, tags=["bot-assignment"], security={"BearerAuth": []})
def check_assignment():
    """Check if a bot is assigned to a guest user"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        if "bot_id" not in data or "guest_user_id" not in data:
            return jsonify(
                {"error": "bot_id and guest_user_id are required"}
            ), HTTPStatus.BAD_REQUEST

        is_assigned = bot_assignment_svc.is_bot_assigned_to_user(
            data["bot_id"], data["guest_user_id"]
        )
        return jsonify({"is_assigned": is_assigned}), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Assignment check error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
