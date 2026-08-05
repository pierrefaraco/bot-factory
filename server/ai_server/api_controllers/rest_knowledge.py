"""Context management REST API Controller"""

import json
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from marshmallow import Schema, fields, ValidationError

from ai_server.exceptions.api_error import ApiError
from ai_server.log.app_logger import AppLogger
from ai_server.services.knowledge_svc import KnowledgeSvc
from ai_server.services.template_svc import TemplateSvc
from ai_server.dao.database import db, User, ROOT_CHAPTER_ID
from ai_server.decorators.role_required import role_required
from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.api_controllers.rest_rag import knowledge_svc
from ai_server.api_controllers.rest_bot import bot_svc

CONTROLLER_NAME = "knowledge"
CONTROLLER_PATH = "/knowledge"

bp = Blueprint(CONTROLLER_NAME, __name__)


class KnowledgeSchema(Schema):
    """Schema for knowledge validation"""

    id = fields.Integer(required=False)
    name = fields.String(required=False, validate=lambda x: len(x.strip()) > 0)
    content = fields.String(required=False)
    knowledge_dad_id = fields.String(required=False, load_default=ROOT_CHAPTER_ID)
    indice = fields.Integer(required=False, load_default=0)
    children = fields.List(fields.String(required=False))
    children_ref_id = fields.String(required=False)
    level = fields.Integer(required=False)
    pdf_file = fields.String(required=False, allow_none=True)
    date = fields.String(required=False, allow_none=True)


class PatchKnowledgeSchema(Schema):
    """Schema for bot parameters patch validation"""

    parameters = fields.Dict(required=True)


class ImportedChaptersSchema(Schema):
    """Schema for imported knowledges validation"""

    importedChapters = fields.List(fields.Dict(), required=True)


# Services initialization
logger = AppLogger()
template_svc = TemplateSvc()
knowledge_schema = KnowledgeSchema()
imported_knowledges_schema = ImportedChaptersSchema()
patch_knowledge_schema = PatchKnowledgeSchema()


@bp.route(
    f"{CONTROLLER_PATH}/save/<int:bot_id>/<knowledge_dad_id>", methods=["POST", "PUT"]
)
@role_required([ADMIN_ROLE, USER_ROLE])
def create_empty_knowledge(bot_id, knowledge_dad_id):
    """Save or update a knowledge"""
    try:
        knowledge = knowledge_svc.create_empty_knowledge(bot_id, knowledge_dad_id)
        return jsonify(knowledge.to_dict()), HTTPStatus.OK
    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"Chapter save error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/save/<int:bot_id>", methods=["POST", "PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
def save_knowledge(bot_id):
    """Save or update a knowledge"""
    try:
        file = None
        if "pdf" in request.files:
            file = request.files["pdf"]

        data = {}
        json_data = request.form.get("data")
        if json_data:
            data = json.loads(json_data)
        validated_data = knowledge_schema.load(data)

        knowledge = knowledge_svc.save_knowledge(
            validated_data.get("pdf_file"),
            bot_id,
            validated_data.get("id"),
            validated_data.get("name"),
            validated_data.get("content"),
            knowledge_dad_id=validated_data["knowledge_dad_id"],
            indice=validated_data["indice"],
            file=file,
        )
        return jsonify(knowledge.to_dict()), HTTPStatus.OK

    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"Chapter save error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:knowledge_id>", methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE])
def patch_knowledge_admin(knowledge_id):
    """Patch bot parameters"""
    try:
        data = request.get_json()
        validated_data = patch_knowledge_schema(data)
    except Exception as exc:
        logger.error(f"Chapter save error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/save_knowledges/<int:bot_id>", methods=["POST", "PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
def save_imported_knowledges(bot_id):
    """Save imported knowledges"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), HTTPStatus.BAD_REQUEST

        validated_data = imported_knowledges_schema.load(data)
        user_id = get_jwt_identity()

        imported_knowledges = validated_data["importedChapters"]
        if imported_knowledges and not bot_svc.is_bot_belong_to_user(
            imported_knowledges[0].get("bot_id"), user_id
        ):
            return jsonify(
                {
                    "error": f"User {user_id} is not allowed to save knowledges for bot {bot_id}"
                }
            ), HTTPStatus.FORBIDDEN

        knowledges = knowledge_svc.save_imported_knowledges(bot_id, imported_knowledges)
        return jsonify([knowledge.to_dict() for knowledge in knowledges]), HTTPStatus.OK

    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"Imported knowledges save error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
def get_knowledges(bot_id):
    """Get all knowledges for a bot"""
    try:
        user_id = get_jwt_identity()
        knowledges = knowledge_svc.get_knowledges(bot_id)
        knowledges_dict = [knowledge.to_dict() for knowledge in knowledges]
        return jsonify(knowledges_dict), HTTPStatus.OK

    except Exception as exc:
        logger.error(f"Get knowledges error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>/<int:knowledge_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
def get_knowledge(bot_id, knowledge_id):
    """Get a specific knowledge"""
    try:
        user_id = get_jwt_identity()
        knowledge = knowledge_svc.get_knowledge(bot_id, knowledge_id)
        if not knowledge:
            return jsonify({"error": "Chapter not found"}), HTTPStatus.NOT_FOUND
        return jsonify(knowledge.to_dict()), HTTPStatus.OK

    except Exception as exc:
        logger.error(f"Get knowledge error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:knowledge_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
def delete_knowledge(knowledge_id):
    """Delete a specific knowledge"""
    try:
        user_id = get_jwt_identity()
        logger.info(f"User {user_id} deleting knowledge {knowledge_id}")

        success = knowledge_svc.delete_knowledge(knowledge_id)
        if not success:
            return jsonify({"error": "Chapter not found"}), HTTPStatus.NOT_FOUND

        return jsonify({"message": "Chapter deleted successfully"}), HTTPStatus.OK

    except Exception as exc:
        logger.error(f"Delete knowledge error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/all/<int:bot_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
def delete_all_knowledges(bot_id):
    """Delete all knowledges for a bot"""
    try:
        user_id = get_jwt_identity()
        logger.info(f"User {user_id} deleting all knowledges for bot {bot_id}")

        success = knowledge_svc.delete_all(bot_id)
        if not success:
            return jsonify(
                {"error": "No knowledges found for this bot"}
            ), HTTPStatus.NOT_FOUND

        return jsonify(
            {"message": "All knowledges deleted successfully"}
        ), HTTPStatus.OK

    except Exception as exc:
        logger.error(f"Delete all knowledges error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(
    f"{CONTROLLER_PATH}/load_template/<int:bot_id>/<template_name>", methods=["GET"]
)
@role_required([ADMIN_ROLE, USER_ROLE])
def load_template(bot_id, template_name):
    """Load a template into the database for a bot"""
    try:
        user_id = get_jwt_identity()
        logger.info(f"User {user_id} loading template {template_name} for bot {bot_id}")

        if not template_name or not template_name.strip():
            return jsonify(
                {"error": "Template name is required"}
            ), HTTPStatus.BAD_REQUEST

        result = template_svc.importTemplateInDB(bot_id, template_name)
        return jsonify(result), HTTPStatus.OK

    except Exception as exc:
        logger.error(f"Template loading error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
