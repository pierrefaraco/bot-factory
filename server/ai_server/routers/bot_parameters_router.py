"""Bot Parameters REST API -- native FastAPI port of the former
ai_server/rest/rest_bot_parameters.py Flask blueprint (Phase 3 of the
Flask -> FastAPI migration). Same URLs, same response shapes, same role
checks; unhandled exceptions fall through to asgi.py's catch-all 500
handler.

Content-Type contract: same situation as rest_avatar.py (no
@bp.before_request guard) -- see dependencies/content_type.py's
require_json_body() docstring. BotParametersPatchRequest has zero
declared fields (extra="allow" only), so like AvatarPatchRequest a wrong
Content-Type falls through to the explicit "Content-Type must be
application/json" message rather than a "Field required" one.

The original patch handler's `if user.roles not in [ADMIN_ROLE,
USER_ROLE]: 403` and its "TODO: Add proper permission check for bot
ownership" are both left exactly as they were: the role check is
unreachable dead code (role_required's FastAPI equivalent,
require_roles(), already rejects any other role before this handler
runs), and bot-ownership scoping was never implemented in the original
either -- not something to add silently as part of a framework-only
migration.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dao.database import User
from ai_server.dependencies.auth import require_roles
from ai_server.dependencies.content_type import require_json_body
from ai_server.dependencies.db_session import with_db_session
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.bot_parameters_svc import BotParametersService

router = APIRouter(prefix="/api/bot-parameters", tags=["bot-parameters"])

logger = BotFactoryLogger()
bot_parameters_svc = BotParametersService()

admin_or_user = require_roles([ADMIN_ROLE, USER_ROLE])
any_role = require_roles([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])


class BotParametersRequest(BaseModel):
    """Schema for bot parameters validation"""

    bot_id: int
    answer_length: Optional[str] = None
    answer_style: Optional[str] = None
    behaviour_when_ignore: Optional[str] = None
    behaviour_with_language: Optional[str] = None
    bot_name: Optional[str] = None
    bot_type: Optional[str] = None
    context_type: Optional[str] = None
    goal: Optional[str] = None
    interlocutor_identity: Optional[str] = None
    interlocutor_type: Optional[str] = None
    localisation: Optional[str] = None
    main_personality_trait_1: Optional[str] = None
    main_personality_trait_2: Optional[str] = None
    main_personality_trait_3: Optional[str] = None
    used_sources: Optional[str] = None
    answer_format: Optional[str] = None
    voice_output: Optional[bool] = None
    persona_description: Optional[str] = None


class BotParametersPatchRequest(BaseModel):
    """Schema for bot parameters patch validation: any subset of the
    BotParametersRequest fields (all optional)"""

    model_config = ConfigDict(extra="allow")


@router.api_route(
    "",
    methods=["POST", "PUT"],
    status_code=201,
    dependencies=[Depends(require_json_body(BotParametersRequest))],
)
@with_db_session
def create_or_update_bot_parameters(
    body: BotParametersRequest, claims: dict = Depends(admin_or_user)
):
    """Create bot parameters and regenerate the bot's system prompt."""
    logger.info("POST/PUT /bot-parameters - create_or_update_bot_parameters called")
    validated_data = body.model_dump(exclude_unset=True)

    user_id = claims["sub"]
    user: User = User.query.filter_by(id=user_id).first()
    if not user:
        logger.warning(f"create_or_update_bot_parameters rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    bot_parameters_dto = bot_parameters_svc.create_bot_parameters(
        user.name, validated_data["bot_id"], validated_data
    )
    logger.info(
        f"create_or_update_bot_parameters succeeded for bot_id={validated_data['bot_id']} "
        f"user_id={user_id}"
    )
    return bot_parameters_dto.to_dict()


@router.patch(
    "/{bot_id}",
    dependencies=[Depends(require_json_body(BotParametersPatchRequest))],
)
@with_db_session
def patch_bot_parameters_admin(
    bot_id: int, body: BotParametersPatchRequest, claims: dict = Depends(admin_or_user)
):
    """Partially update bot parameters and regenerate the bot's system prompt.

    Empty-string values are ignored, except for the optional clearable
    fields (persona_description, answer_format)."""
    logger.info(f"PATCH /bot-parameters/{bot_id} - patch_bot_parameters_admin called")
    validated_data = body.model_dump()

    user_id = claims["sub"]
    user: User = User.query.filter_by(id=user_id).first()
    if not user:
        logger.warning(f"patch_bot_parameters_admin({bot_id}) rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    bot_parameters_dto = bot_parameters_svc.patch_bot_parameters(bot_id, validated_data, user.name)
    if not bot_parameters_dto:
        logger.warning(f"patch_bot_parameters_admin({bot_id}) not found")
        raise ApiError("Bot parameters not found", status_code=404)

    logger.info(f"patch_bot_parameters_admin({bot_id}) succeeded")
    return bot_parameters_dto.to_dict()


@router.get("/{bot_id}", dependencies=[Depends(any_role)])
@with_db_session
def get_bot_parameters_by_bot_id(bot_id: int):
    """Get bot parameters by bot ID"""
    logger.info(f"GET /bot-parameters/{bot_id} - get_bot_parameters_by_bot_id called")
    bot_parameters_dto = bot_parameters_svc.get_by_bot_id(bot_id)
    if not bot_parameters_dto:
        logger.warning(f"get_bot_parameters_by_bot_id({bot_id}) not found")
        raise ApiError("Bot parameters not found", status_code=404)
    logger.info(f"get_bot_parameters_by_bot_id({bot_id}) succeeded")
    return bot_parameters_dto.to_dict()


@router.delete("/{bot_id}", status_code=204, dependencies=[Depends(admin_or_user)])
@with_db_session
def delete_bot_parameters(bot_id: int):
    """Delete bot parameters by bot ID"""
    logger.info(f"DELETE /bot-parameters/{bot_id} - delete_bot_parameters called")
    if not bot_parameters_svc.delete_by_bot_id(bot_id):
        logger.warning(f"delete_bot_parameters({bot_id}) not found")
        raise ApiError("Bot parameters not found", status_code=404)
    logger.info(f"delete_bot_parameters({bot_id}) succeeded")
    return Response(status_code=204)
