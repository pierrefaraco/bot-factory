"""Context management REST API Controller"""

import json
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError

from ai_server.config.openapi import api, pydantic_error_messages

from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
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


class KnowledgeRequest(BaseModel):
    """Schema for knowledge validation"""

    id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=1)
    content: Optional[str] = None
    knowledge_dad_id: str = ROOT_CHAPTER_ID
    indice: int = 0
    children: Optional[List[str]] = None
    children_ref_id: Optional[str] = None
    level: Optional[int] = None
    pdf_file: Optional[str] = None
    date: Optional[str] = None


class ImportedChaptersRequest(BaseModel):
    """Schema for imported knowledges validation"""

    importedChapters: List[dict]


# Services initialization
logger = BotFactoryLogger()
template_svc = TemplateSvc()


@bp.route(
    f"{CONTROLLER_PATH}/save/<int:bot_id>/<knowledge_dad_id>", methods=["POST", "PUT"]
)
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
def create_empty_knowledge(bot_id, knowledge_dad_id):
    """Save or update a knowledge"""
    try:
        knowledge = knowledge_svc.create_empty_knowledge(bot_id, knowledge_dad_id)
        return jsonify(knowledge.to_dict()), HTTPStatus.OK
    except ValidationError as e:
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"Chapter save error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/save/<int:bot_id>", methods=["POST", "PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
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
        validated_data = KnowledgeRequest.model_validate(data).model_dump()

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
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"Chapter save error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:knowledge_id>", methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
def patch_knowledge_admin(knowledge_id):
    """Patch a knowledge chapter (not implemented yet)"""
    return jsonify({"error": "Not implemented"}), HTTPStatus.NOT_IMPLEMENTED


@bp.route(f"{CONTROLLER_PATH}/save_knowledges/<int:bot_id>", methods=["POST", "PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=ImportedChaptersRequest, tags=["knowledge"], security={"BearerAuth": []})
def save_imported_knowledges(bot_id):
    """Save imported knowledges"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), HTTPStatus.BAD_REQUEST

        validated_data = ImportedChaptersRequest.model_validate(data).model_dump()
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
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"Imported knowledges save error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
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
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
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
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
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
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
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
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
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
