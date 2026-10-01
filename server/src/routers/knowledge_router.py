"""Knowledge base REST API.

save_knowledge takes multipart/form-data: an optional "pdf" file field
plus an optional "data" text field holding a JSON string (not a JSON
body). The blocking parts (ChromaDB, PDF file writes) run through
run_in_threadpool inside knowledge_svc.py.
"""

import json
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field, ValidationError

from src.config.constant import ADMIN_ROLE, USER_ROLE
from src.config.validation import pydantic_error_messages
from src.models import ROOT_CHAPTER_ID
from src.dependencies.auth import require_roles
from src.dependencies.content_type import require_json_body
from src.dependencies.db_session import async_db_session_dependency
from src.dependencies.services import (
    BotServiceDep,
    KnowledgeServiceDep,
    TemplateServiceDep,
)
from src.exceptions.api_error import ApiError
from src.log.bot_factory_logger import BotFactoryLogger
from src.services.knowledge_svc import InvalidPdfError

router = APIRouter(
    prefix="/api/knowledge",
    tags=["knowledge"],
    dependencies=[Depends(async_db_session_dependency)],
)

logger = BotFactoryLogger()

admin_or_user = require_roles([ADMIN_ROLE, USER_ROLE])


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


@router.post("/save/{bot_id:int}/{knowledge_dad_id}", dependencies=[Depends(admin_or_user)])
@router.put("/save/{bot_id:int}/{knowledge_dad_id}", dependencies=[Depends(admin_or_user)])
async def create_empty_knowledge(
    bot_id: int,
    knowledge_dad_id: str,
    knowledge_svc: KnowledgeServiceDep,
):
    """Save or update a knowledge"""
    logger.info(f"POST/PUT /knowledge/save/{bot_id}/{knowledge_dad_id} - create_empty_knowledge called")
    knowledge = await knowledge_svc.create_empty_knowledge(bot_id, knowledge_dad_id)
    logger.info(f"create_empty_knowledge succeeded bot_id={bot_id} knowledge_id={knowledge.id}")
    return knowledge.to_dict()


@router.post("/save/{bot_id:int}", dependencies=[Depends(admin_or_user)])
@router.put("/save/{bot_id:int}", dependencies=[Depends(admin_or_user)])
async def save_knowledge(
    bot_id: int,
    knowledge_svc: KnowledgeServiceDep,
    pdf: Optional[UploadFile] = File(default=None),
    data: Optional[str] = Form(default=None),
):
    """Save or update a knowledge"""
    logger.info(f"POST/PUT /knowledge/save/{bot_id} - save_knowledge called")
    parsed_data = {}
    if data:
        parsed_data = json.loads(data)
    try:
        validated_data = KnowledgeRequest.model_validate(parsed_data).model_dump()
    except ValidationError as e:
        logger.warning(f"save_knowledge validation error: {pydantic_error_messages(e)}")
        raise ApiError(pydantic_error_messages(e), status_code=400) from e

    logger.debug(
        f"save_knowledge(bot_id={bot_id}) params: id={validated_data.get('id')} "
        f"name={validated_data.get('name')} knowledge_dad_id={validated_data.get('knowledge_dad_id')} "
        f"has_pdf_file={bool(pdf)}"
    )

    pdf_name = validated_data.get("pdf_file") or (pdf.filename if pdf else None)
    try:
        knowledge = await knowledge_svc.save_knowledge(
            pdf_name,
            bot_id,
            validated_data.get("id"),
            validated_data.get("name"),
            validated_data.get("content"),
            knowledge_dad_id=validated_data["knowledge_dad_id"],
            indice=validated_data["indice"],
            file=pdf.file if pdf is not None else None,
        )
    except InvalidPdfError as e:
        raise ApiError(str(e), status_code=400) from e
    logger.info(f"save_knowledge succeeded bot_id={bot_id} knowledge_id={knowledge.id}")
    return knowledge.to_dict()


@router.patch("/{knowledge_id:int}", status_code=501, dependencies=[Depends(admin_or_user)])
async def patch_knowledge_admin(knowledge_id: int):
    """Patch a knowledge chapter (not implemented yet)"""
    logger.info(f"PATCH /knowledge/{knowledge_id} - patch_knowledge_admin called")
    logger.warning(f"patch_knowledge_admin({knowledge_id}) not implemented")
    return {"error": "Not implemented"}


@router.post(
    "/save_knowledges/{bot_id:int}",
    dependencies=[Depends(require_json_body(ImportedChaptersRequest))],
)
@router.put(
    "/save_knowledges/{bot_id:int}",
    dependencies=[Depends(require_json_body(ImportedChaptersRequest))],
)
async def save_imported_knowledges(
    bot_id: int,
    body: ImportedChaptersRequest,
    knowledge_svc: KnowledgeServiceDep,
    bot_svc: BotServiceDep,
    claims: dict = Depends(admin_or_user),
):
    """Save imported knowledges"""
    logger.info(f"POST/PUT /knowledge/save_knowledges/{bot_id} - save_imported_knowledges called")
    user_id = claims["sub"]
    imported_knowledges = body.importedChapters
    logger.debug(
        f"save_imported_knowledges(bot_id={bot_id}) params: "
        f"count={len(imported_knowledges)} user_id={user_id}"
    )
    if imported_knowledges and not await bot_svc.is_bot_belong_to_user(bot_id, user_id):
        logger.warning(f"save_imported_knowledges(bot_id={bot_id}) forbidden for user_id={user_id}")
        raise ApiError(
            f"User {user_id} is not allowed to save knowledges for bot {bot_id}",
            status_code=403,
        )

    knowledges = await knowledge_svc.save_imported_knowledges(
        bot_id, imported_knowledges
    )
    logger.info(f"save_imported_knowledges succeeded bot_id={bot_id} count={len(knowledges)}")
    return [knowledge.to_dict() for knowledge in knowledges]


@router.get("/{bot_id:int}", dependencies=[Depends(admin_or_user)])
async def get_knowledges(
    bot_id: int,
    knowledge_svc: KnowledgeServiceDep,
    claims: dict = Depends(admin_or_user),
):
    """Get all knowledges for a bot"""
    logger.info(f"GET /knowledge/{bot_id} - get_knowledges called")
    user_id = claims["sub"]
    knowledges = await knowledge_svc.get_knowledges(bot_id)
    knowledges_dict = [knowledge.to_dict() for knowledge in knowledges]
    logger.info(f"get_knowledges succeeded bot_id={bot_id} user_id={user_id} count={len(knowledges_dict)}")
    return knowledges_dict


@router.get("/{bot_id:int}/{knowledge_id:int}", dependencies=[Depends(admin_or_user)])
async def get_knowledge(
    bot_id: int,
    knowledge_id: int,
    knowledge_svc: KnowledgeServiceDep,
    claims: dict = Depends(admin_or_user),
):
    """Get a specific knowledge"""
    logger.info(f"GET /knowledge/{bot_id}/{knowledge_id} - get_knowledge called")
    user_id = claims["sub"]
    knowledge = await knowledge_svc.get_knowledge(bot_id, knowledge_id)
    if not knowledge:
        logger.warning(f"get_knowledge(bot_id={bot_id}, knowledge_id={knowledge_id}) not found")
        raise ApiError("Chapter not found", status_code=404)
    logger.info(f"get_knowledge succeeded bot_id={bot_id} knowledge_id={knowledge_id} user_id={user_id}")
    return knowledge.to_dict()


@router.delete("/{knowledge_id:int}", dependencies=[Depends(admin_or_user)])
async def delete_knowledge(
    knowledge_id: int,
    knowledge_svc: KnowledgeServiceDep,
    claims: dict = Depends(admin_or_user),
):
    """Delete a specific knowledge"""
    logger.info(f"DELETE /knowledge/{knowledge_id} - delete_knowledge called")
    user_id = claims["sub"]
    logger.info(f"User {user_id} deleting knowledge {knowledge_id}")

    if not await knowledge_svc.delete_knowledge(knowledge_id):
        logger.warning(f"delete_knowledge({knowledge_id}) not found")
        raise ApiError("Chapter not found", status_code=404)

    logger.info(f"delete_knowledge({knowledge_id}) succeeded")
    return {"message": "Chapter deleted successfully"}


@router.delete("/all/{bot_id:int}", dependencies=[Depends(admin_or_user)])
async def delete_all_knowledges(
    bot_id: int,
    knowledge_svc: KnowledgeServiceDep,
    claims: dict = Depends(admin_or_user),
):
    """Delete all knowledges for a bot"""
    logger.info(f"DELETE /knowledge/all/{bot_id} - delete_all_knowledges called")
    user_id = claims["sub"]
    logger.info(f"User {user_id} deleting all knowledges for bot {bot_id}")

    if not await knowledge_svc.delete_all(bot_id):
        logger.warning(f"delete_all_knowledges(bot_id={bot_id}) not found")
        raise ApiError("No knowledges found for this bot", status_code=404)

    logger.info(f"delete_all_knowledges(bot_id={bot_id}) succeeded")
    return {"message": "All knowledges deleted successfully"}


@router.get("/load_template/{bot_id:int}/{template_name}", dependencies=[Depends(admin_or_user)])
async def load_template(
    bot_id: int,
    template_name: str,
    template_svc: TemplateServiceDep,
    claims: dict = Depends(admin_or_user),
):
    """Load a template into the database for a bot"""
    logger.info(f"GET /knowledge/load_template/{bot_id}/{template_name} - load_template called")
    user_id = claims["sub"]
    logger.info(f"User {user_id} loading template {template_name} for bot {bot_id}")

    if not template_name or not template_name.strip():
        logger.warning(f"load_template(bot_id={bot_id}) rejected: missing template name")
        raise ApiError("Template name is required", status_code=400)

    start_time = time.monotonic()
    result = await template_svc.importTemplateInDB(bot_id, template_name)
    duration_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        f"load_template succeeded bot_id={bot_id} template_name={template_name} "
        f"duration_ms={duration_ms:.1f}"
    )
    return result
