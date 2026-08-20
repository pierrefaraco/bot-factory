"""Context management REST API Controller"""

import json
import time
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
from ai_server.rest.rest_rag import knowledge_svc
from ai_server.rest.rest_bot import bot_svc

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
    logger.info(
        f"POST/PUT {CONTROLLER_PATH}/save/{bot_id}/{knowledge_dad_id} - create_empty_knowledge called"
    )
    try:
        knowledge = knowledge_svc.create_empty_knowledge(bot_id, knowledge_dad_id)
        logger.info(
            f"create_empty_knowledge succeeded bot_id={bot_id} knowledge_id={knowledge.id} "
            f"- status={HTTPStatus.OK}"
        )
        return jsonify(knowledge.to_dict()), HTTPStatus.OK
    except ValidationError as e:
        logger.warning(f"create_empty_knowledge validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.exception(f"Chapter save error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/save/<int:bot_id>", methods=["POST", "PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
def save_knowledge(bot_id):
    """Save or update a knowledge"""
    logger.info(f"POST/PUT {CONTROLLER_PATH}/save/{bot_id} - save_knowledge called")
    try:
        file = None
        if "pdf" in request.files:
            file = request.files["pdf"]

        data = {}
        json_data = request.form.get("data")
        if json_data:
            data = json.loads(json_data)
        validated_data = KnowledgeRequest.model_validate(data).model_dump()
        logger.debug(
            f"save_knowledge(bot_id={bot_id}) params: id={validated_data.get('id')} "
            f"name={validated_data.get('name')} knowledge_dad_id={validated_data.get('knowledge_dad_id')} "
            f"has_pdf_file={bool(file)}"
        )

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
        logger.info(
            f"save_knowledge succeeded bot_id={bot_id} knowledge_id={knowledge.id} "
            f"- status={HTTPStatus.OK}"
        )
        return jsonify(knowledge.to_dict()), HTTPStatus.OK

    except ValidationError as e:
        logger.warning(f"save_knowledge validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.exception(f"Chapter save error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:knowledge_id>", methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
def patch_knowledge_admin(knowledge_id):
    """Patch a knowledge chapter (not implemented yet)"""
    logger.info(f"PATCH {CONTROLLER_PATH}/{knowledge_id} - patch_knowledge_admin called")
    logger.warning(f"patch_knowledge_admin({knowledge_id}) not implemented")
    return jsonify({"error": "Not implemented"}), HTTPStatus.NOT_IMPLEMENTED


@bp.route(f"{CONTROLLER_PATH}/save_knowledges/<int:bot_id>", methods=["POST", "PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=ImportedChaptersRequest, tags=["knowledge"], security={"BearerAuth": []})
def save_imported_knowledges(bot_id):
    """Save imported knowledges"""
    logger.info(f"POST/PUT {CONTROLLER_PATH}/save_knowledges/{bot_id} - save_imported_knowledges called")
    try:
        data = request.get_json()
        if not data:
            logger.warning(f"save_imported_knowledges(bot_id={bot_id}) rejected: no data provided")
            return jsonify({"error": "No data provided"}), HTTPStatus.BAD_REQUEST

        validated_data = ImportedChaptersRequest.model_validate(data).model_dump()
        user_id = get_jwt_identity()

        imported_knowledges = validated_data["importedChapters"]
        logger.debug(
            f"save_imported_knowledges(bot_id={bot_id}) params: "
            f"count={len(imported_knowledges)} user_id={user_id}"
        )
        if imported_knowledges and not bot_svc.is_bot_belong_to_user(
            imported_knowledges[0].get("bot_id"), user_id
        ):
            logger.warning(
                f"save_imported_knowledges(bot_id={bot_id}) forbidden for user_id={user_id}"
            )
            return jsonify(
                {
                    "error": f"User {user_id} is not allowed to save knowledges for bot {bot_id}"
                }
            ), HTTPStatus.FORBIDDEN

        knowledges = knowledge_svc.save_imported_knowledges(bot_id, imported_knowledges)
        logger.info(
            f"save_imported_knowledges succeeded bot_id={bot_id} count={len(knowledges)} "
            f"- status={HTTPStatus.OK}"
        )
        return jsonify([knowledge.to_dict() for knowledge in knowledges]), HTTPStatus.OK

    except ValidationError as e:
        logger.warning(f"save_imported_knowledges validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.exception(f"Imported knowledges save error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
def get_knowledges(bot_id):
    """Get all knowledges for a bot"""
    logger.info(f"GET {CONTROLLER_PATH}/{bot_id} - get_knowledges called")
    try:
        user_id = get_jwt_identity()
        knowledges = knowledge_svc.get_knowledges(bot_id)
        knowledges_dict = [knowledge.to_dict() for knowledge in knowledges]
        logger.info(
            f"get_knowledges succeeded bot_id={bot_id} user_id={user_id} "
            f"count={len(knowledges_dict)} - status={HTTPStatus.OK}"
        )
        return jsonify(knowledges_dict), HTTPStatus.OK

    except Exception as exc:
        logger.exception(f"Get knowledges error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>/<int:knowledge_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
def get_knowledge(bot_id, knowledge_id):
    """Get a specific knowledge"""
    logger.info(f"GET {CONTROLLER_PATH}/{bot_id}/{knowledge_id} - get_knowledge called")
    try:
        user_id = get_jwt_identity()
        knowledge = knowledge_svc.get_knowledge(bot_id, knowledge_id)
        if not knowledge:
            logger.warning(f"get_knowledge(bot_id={bot_id}, knowledge_id={knowledge_id}) not found")
            return jsonify({"error": "Chapter not found"}), HTTPStatus.NOT_FOUND
        logger.info(
            f"get_knowledge succeeded bot_id={bot_id} knowledge_id={knowledge_id} "
            f"user_id={user_id} - status={HTTPStatus.OK}"
        )
        return jsonify(knowledge.to_dict()), HTTPStatus.OK

    except Exception as exc:
        logger.exception(f"Get knowledge error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:knowledge_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
def delete_knowledge(knowledge_id):
    """Delete a specific knowledge"""
    logger.info(f"DELETE {CONTROLLER_PATH}/{knowledge_id} - delete_knowledge called")
    try:
        user_id = get_jwt_identity()
        logger.info(f"User {user_id} deleting knowledge {knowledge_id}")

        success = knowledge_svc.delete_knowledge(knowledge_id)
        if not success:
            logger.warning(f"delete_knowledge({knowledge_id}) not found")
            return jsonify({"error": "Chapter not found"}), HTTPStatus.NOT_FOUND

        logger.info(f"delete_knowledge({knowledge_id}) succeeded - status={HTTPStatus.OK}")
        return jsonify({"message": "Chapter deleted successfully"}), HTTPStatus.OK

    except Exception as exc:
        logger.exception(f"Delete knowledge error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/all/<int:bot_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["knowledge"], security={"BearerAuth": []})
def delete_all_knowledges(bot_id):
    """Delete all knowledges for a bot"""
    logger.info(f"DELETE {CONTROLLER_PATH}/all/{bot_id} - delete_all_knowledges called")
    try:
        user_id = get_jwt_identity()
        logger.info(f"User {user_id} deleting all knowledges for bot {bot_id}")

        success = knowledge_svc.delete_all(bot_id)
        if not success:
            logger.warning(f"delete_all_knowledges(bot_id={bot_id}) not found")
            return jsonify(
                {"error": "No knowledges found for this bot"}
            ), HTTPStatus.NOT_FOUND

        logger.info(f"delete_all_knowledges(bot_id={bot_id}) succeeded - status={HTTPStatus.OK}")
        return jsonify(
            {"message": "All knowledges deleted successfully"}
        ), HTTPStatus.OK

    except Exception as exc:
        logger.exception(f"Delete all knowledges error: {exc}")
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
    logger.info(
        f"GET {CONTROLLER_PATH}/load_template/{bot_id}/{template_name} - load_template called"
    )
    try:
        user_id = get_jwt_identity()
        logger.info(f"User {user_id} loading template {template_name} for bot {bot_id}")

        if not template_name or not template_name.strip():
            logger.warning(f"load_template(bot_id={bot_id}) rejected: missing template name")
            return jsonify(
                {"error": "Template name is required"}
            ), HTTPStatus.BAD_REQUEST

        start_time = time.monotonic()
        result = template_svc.importTemplateInDB(bot_id, template_name)
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            f"load_template succeeded bot_id={bot_id} template_name={template_name} "
            f"duration_ms={duration_ms:.1f} - status={HTTPStatus.OK}"
        )
        return jsonify(result), HTTPStatus.OK

    except Exception as exc:
        logger.exception(f"Template loading error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
