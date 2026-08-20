"""Knowledge base REST API -- native FastAPI port of the former
ai_server/rest/rest_knowledge.py Flask blueprint (Phase 6 of the
Flask -> FastAPI migration). Same URLs, same response shapes, same role
checks; unhandled exceptions fall through to asgi.py's catch-all 500
handler.

save_knowledge is the first migrated route to take a file upload
(multipart/form-data: an optional "pdf" file field + an optional "data"
text field holding a JSON string -- not a JSON body). FastAPI represents
that upload as an UploadFile, which has no .save(path) method the way
Flask's FileStorage does; knowledge_svc.save_pdf() calls file.save(...)
directly. Rather than change that service method's file-object contract
(a business-logic file), _FlaskFileStorageAdapter below gives the
UploadFile a .save() of its own at the router boundary -- keeping the
Flask-shaped API service-side and only adapting at the framework edge.

ImportedChaptersRequest/KnowledgeRequest's manual `if not data` /
`if not request.is_json` guards in the original were dead code exactly
like in previous phases (a required `importedChapters` field means an
absent/empty body already 400s via SpecTree's own gate first) --
skipped here in favor of reading straight off the validated body model.
"""

import json
import shutil
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field, ValidationError

from ai_server.config.constant import ADMIN_ROLE, USER_ROLE
from ai_server.config.validation import pydantic_error_messages
from ai_server.dao.database import ROOT_CHAPTER_ID
from ai_server.dependencies.auth import require_roles
from ai_server.dependencies.content_type import require_json_body
from ai_server.dependencies.db_session import with_db_session
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.bot_svc import BotService
from ai_server.services.knowledge_svc import KnowledgeSvc
from ai_server.services.rag_svc import RagService
from ai_server.services.template_svc import TemplateSvc

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

logger = BotFactoryLogger()
knowledge_svc = KnowledgeSvc(RagService())
template_svc = TemplateSvc()
bot_svc = BotService()

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


class _FlaskFileStorageAdapter:
    """Gives a FastAPI UploadFile the .save(path) method
    knowledge_svc.save_pdf() expects from a Flask FileStorage."""

    def __init__(self, upload_file: UploadFile):
        self._upload_file = upload_file

    def save(self, dst: str) -> None:
        self._upload_file.file.seek(0)
        with open(dst, "wb") as out:
            shutil.copyfileobj(self._upload_file.file, out)


@router.post("/save/{bot_id:int}/{knowledge_dad_id}", dependencies=[Depends(admin_or_user)])
@router.put("/save/{bot_id:int}/{knowledge_dad_id}", dependencies=[Depends(admin_or_user)])
@with_db_session
def create_empty_knowledge(bot_id: int, knowledge_dad_id: str):
    """Save or update a knowledge"""
    logger.info(f"POST/PUT /knowledge/save/{bot_id}/{knowledge_dad_id} - create_empty_knowledge called")
    knowledge = knowledge_svc.create_empty_knowledge(bot_id, knowledge_dad_id)
    logger.info(f"create_empty_knowledge succeeded bot_id={bot_id} knowledge_id={knowledge.id}")
    return knowledge.to_dict()


@router.post("/save/{bot_id:int}", dependencies=[Depends(admin_or_user)])
@router.put("/save/{bot_id:int}", dependencies=[Depends(admin_or_user)])
@with_db_session
def save_knowledge(
    bot_id: int,
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

    file = _FlaskFileStorageAdapter(pdf) if pdf is not None else None
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
    logger.info(f"save_knowledge succeeded bot_id={bot_id} knowledge_id={knowledge.id}")
    return knowledge.to_dict()


@router.patch("/{knowledge_id:int}", status_code=501, dependencies=[Depends(admin_or_user)])
def patch_knowledge_admin(knowledge_id: int):
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
@with_db_session
def save_imported_knowledges(
    bot_id: int, body: ImportedChaptersRequest, claims: dict = Depends(admin_or_user)
):
    """Save imported knowledges"""
    logger.info(f"POST/PUT /knowledge/save_knowledges/{bot_id} - save_imported_knowledges called")
    user_id = claims["sub"]
    imported_knowledges = body.importedChapters
    logger.debug(
        f"save_imported_knowledges(bot_id={bot_id}) params: "
        f"count={len(imported_knowledges)} user_id={user_id}"
    )
    if imported_knowledges and not bot_svc.is_bot_belong_to_user(
        imported_knowledges[0].get("bot_id"), user_id
    ):
        logger.warning(f"save_imported_knowledges(bot_id={bot_id}) forbidden for user_id={user_id}")
        raise ApiError(
            f"User {user_id} is not allowed to save knowledges for bot {bot_id}",
            status_code=403,
        )

    knowledges = knowledge_svc.save_imported_knowledges(bot_id, imported_knowledges)
    logger.info(f"save_imported_knowledges succeeded bot_id={bot_id} count={len(knowledges)}")
    return [knowledge.to_dict() for knowledge in knowledges]


@router.get("/{bot_id:int}", dependencies=[Depends(admin_or_user)])
@with_db_session
def get_knowledges(bot_id: int, claims: dict = Depends(admin_or_user)):
    """Get all knowledges for a bot"""
    logger.info(f"GET /knowledge/{bot_id} - get_knowledges called")
    user_id = claims["sub"]
    knowledges = knowledge_svc.get_knowledges(bot_id)
    knowledges_dict = [knowledge.to_dict() for knowledge in knowledges]
    logger.info(f"get_knowledges succeeded bot_id={bot_id} user_id={user_id} count={len(knowledges_dict)}")
    return knowledges_dict


@router.get("/{bot_id:int}/{knowledge_id:int}", dependencies=[Depends(admin_or_user)])
@with_db_session
def get_knowledge(bot_id: int, knowledge_id: int, claims: dict = Depends(admin_or_user)):
    """Get a specific knowledge"""
    logger.info(f"GET /knowledge/{bot_id}/{knowledge_id} - get_knowledge called")
    user_id = claims["sub"]
    knowledge = knowledge_svc.get_knowledge(bot_id, knowledge_id)
    if not knowledge:
        logger.warning(f"get_knowledge(bot_id={bot_id}, knowledge_id={knowledge_id}) not found")
        raise ApiError("Chapter not found", status_code=404)
    logger.info(f"get_knowledge succeeded bot_id={bot_id} knowledge_id={knowledge_id} user_id={user_id}")
    return knowledge.to_dict()


@router.delete("/{knowledge_id:int}", dependencies=[Depends(admin_or_user)])
@with_db_session
def delete_knowledge(knowledge_id: int, claims: dict = Depends(admin_or_user)):
    """Delete a specific knowledge"""
    logger.info(f"DELETE /knowledge/{knowledge_id} - delete_knowledge called")
    user_id = claims["sub"]
    logger.info(f"User {user_id} deleting knowledge {knowledge_id}")

    if not knowledge_svc.delete_knowledge(knowledge_id):
        logger.warning(f"delete_knowledge({knowledge_id}) not found")
        raise ApiError("Chapter not found", status_code=404)

    logger.info(f"delete_knowledge({knowledge_id}) succeeded")
    return {"message": "Chapter deleted successfully"}


@router.delete("/all/{bot_id:int}", dependencies=[Depends(admin_or_user)])
@with_db_session
def delete_all_knowledges(bot_id: int, claims: dict = Depends(admin_or_user)):
    """Delete all knowledges for a bot"""
    logger.info(f"DELETE /knowledge/all/{bot_id} - delete_all_knowledges called")
    user_id = claims["sub"]
    logger.info(f"User {user_id} deleting all knowledges for bot {bot_id}")

    if not knowledge_svc.delete_all(bot_id):
        logger.warning(f"delete_all_knowledges(bot_id={bot_id}) not found")
        raise ApiError("No knowledges found for this bot", status_code=404)

    logger.info(f"delete_all_knowledges(bot_id={bot_id}) succeeded")
    return {"message": "All knowledges deleted successfully"}


@router.get("/load_template/{bot_id:int}/{template_name}", dependencies=[Depends(admin_or_user)])
@with_db_session
def load_template(bot_id: int, template_name: str, claims: dict = Depends(admin_or_user)):
    """Load a template into the database for a bot"""
    logger.info(f"GET /knowledge/load_template/{bot_id}/{template_name} - load_template called")
    user_id = claims["sub"]
    logger.info(f"User {user_id} loading template {template_name} for bot {bot_id}")

    if not template_name or not template_name.strip():
        logger.warning(f"load_template(bot_id={bot_id}) rejected: missing template name")
        raise ApiError("Template name is required", status_code=400)

    start_time = time.monotonic()
    result = template_svc.importTemplateInDB(bot_id, template_name)
    duration_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        f"load_template succeeded bot_id={bot_id} template_name={template_name} "
        f"duration_ms={duration_ms:.1f}"
    )
    return result
