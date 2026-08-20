"""Bot CRUD REST API -- native FastAPI port of the former
ai_server/rest/rest_bot.py Flask blueprint (Phase 4 of the
Flask -> FastAPI migration). Same URLs, same response shapes, same role
checks and ownership rules; unhandled exceptions fall through to
asgi.py's catch-all 500 handler.

Two deliberate, flagged departures from the original, both on paths no
test exercises:

- The original's blanket `except Exception as e: return jsonify({"error":
  str(e)}), 500` leaked the raw exception text, unlike every other
  migrated blueprint (which returned a generic "Internal server error").
  This port uses the same generic message everywhere instead, for a
  consistent contract and to stop leaking internal error detail -- an
  intentional normalization, not a silent slip.
- update_bot_admin's `BotUpdateRequest.model_validate(data).model_dump(...)
  if data else {}` special-cased an empty/absent JSON body to `{}`
  without validating it; FastAPI's own body parsing will instead 400 on
  a genuinely empty body even with a correct Content-Type header (every
  test here only exercises the *wrong* Content-Type case, which behaves
  identically via require_json_content_type below).

Path params use the `{bot_id:int}` Starlette converter (not a bare
`{bot_id}`) to match Flask's `<int:bot_id>` exactly: a non-numeric
segment falls through to the next route (e.g. "/me", "/owned") instead
of matching here and 422ing.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, field_validator

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dao.database import User, db
from ai_server.dependencies.auth import require_roles
from ai_server.dependencies.content_type import require_json_content_type
from ai_server.dependencies.db_session import with_db_session
from ai_server.dto.bot_dto import BotDto
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.bot_svc import BotService

router = APIRouter(prefix="/api/bot", tags=["bot"])

logger = BotFactoryLogger()
bot_svc = BotService()

admin_or_user = require_roles([ADMIN_ROLE, USER_ROLE])
any_role = require_roles([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])


class BotUpdateRequest(BaseModel):
    """Schema for bot update validation"""

    id: Optional[int] = None
    user_account_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("name must not be blank")
        return value


def _can_modify_bot(user: User, bot_id: int) -> bool:
    if user.roles == ADMIN_ROLE:
        return True
    bot_dto: BotDto = bot_svc.get_dto_by_id(bot_id)
    return bot_dto and bot_dto.user_account_id == user.id


@router.post("", status_code=201, dependencies=[Depends(require_json_content_type)])
@with_db_session
def create_bot(claims: dict = Depends(admin_or_user)):
    """Create a new bot with random parameters for the authenticated user."""
    logger.info("POST /bot - create_bot called")
    user_account_id = claims["sub"]
    if not user_account_id:
        logger.warning("create_bot rejected: missing user id in JWT")
        raise ApiError("User ID is required", status_code=400)

    bot_dto: BotDto = bot_svc.create_random_bot(user_account_id)
    if not bot_dto:
        logger.warning(f"create_bot failed for user_account_id={user_account_id}")
        raise ApiError("Failed to create bot", status_code=500)

    logger.info(f"create_bot succeeded for user_account_id={user_account_id} bot_id={bot_dto.id}")
    return bot_dto.to_dict()


@router.get("/me", dependencies=[Depends(any_role)])
@with_db_session
def get_user_bots(claims: dict = Depends(any_role)):
    """Récupère tous les bots d'un utilisateur"""
    logger.info("GET /bot/me - get_user_bots called")
    user_id = claims["sub"]
    user: User = User.query.filter_by(id=user_id).first()
    if not user:
        logger.warning(f"get_user_bots rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    bots_dto: List[BotDto] = bot_svc.get_owned_and_assigned_bots(user_id)
    logger.info(f"get_user_bots succeeded for user_id={user_id} count={len(bots_dto)}")
    return [bot_dto.to_dict() for bot_dto in bots_dto]


@router.get("", dependencies=[Depends(admin_or_user)])
@with_db_session
def get_all_bots():
    """Récupère tous les bots"""
    logger.info("GET /bot - get_all_bots called")
    bots_dto: List[BotDto] = bot_svc.get_all()
    logger.info(f"get_all_bots succeeded count={len(bots_dto)}")
    return [bot_dto.to_dict() for bot_dto in bots_dto]


@router.get("/owned", dependencies=[Depends(any_role)])
@with_db_session
def get_all_owned_bots(claims: dict = Depends(any_role)):
    """Récupère tous les bots"""
    user_id = claims["sub"]
    logger.info(f"GET /bot/owned - get_all_owned_bots called for user_id={user_id}")
    bots_dto: List[BotDto] = bot_svc.get_bots_by_user(user_id)
    logger.info(f"get_all_owned_bots succeeded for user_id={user_id} count={len(bots_dto)}")
    return [bot_dto.to_dict() for bot_dto in bots_dto]


@router.get("/parameters-description", dependencies=[Depends(admin_or_user)])
@with_db_session
def get_bot_parameters_description():
    logger.info("GET /bot/parameters-description - get_bot_parameters_description called")
    result = bot_svc.get_bot_parameters_description()
    logger.info("get_bot_parameters_description succeeded")
    return result


@router.patch("/selectbot/{bot_id:int}", status_code=204, dependencies=[Depends(any_role)])
@with_db_session
def select_bot(bot_id: int, claims: dict = Depends(any_role)):
    """Select a bot by its ID and user ID."""
    logger.info(f"PATCH /bot/selectbot/{bot_id} - select_bot called")
    user_id = claims["sub"]
    user: User = User.query.filter_by(id=user_id).first()
    if not user:
        logger.warning(f"select_bot({bot_id}) rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    user.selected_bot_id = bot_id
    db.session.commit()
    logger.info(f"select_bot({bot_id}) succeeded for user_id={user_id}")
    return Response(status_code=204)


@router.get("/{bot_id:int}", dependencies=[Depends(any_role)])
@with_db_session
def get_bot(bot_id: int, claims: dict = Depends(any_role), view: str = Query(default="minimal")):
    """Get a bot by its ID."""
    logger.info(f"GET /bot/{bot_id} - get_bot called")
    user_id = claims["sub"]
    user: User = User.query.filter_by(id=user_id).first()
    if not user:
        logger.warning(f"get_bot({bot_id}) rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    logger.debug(f"get_bot({bot_id}) params: view={view}")
    bot_dto: Optional[BotDto] = bot_svc.get_dto_by_id(bot_id, view)
    if not bot_dto:
        logger.warning(f"get_bot({bot_id}) not found")
        raise ApiError("Bot not found", status_code=404)

    if user.roles == ADMIN_ROLE:
        logger.info(f"get_bot({bot_id}) succeeded")
        return bot_dto.to_dict()
    elif user.roles in (USER_ROLE, GUEST_ROLE):
        if int(bot_dto.user_account_id) == int(user_id) or bot_svc.is_bot_assigned_to_user(bot_id, user_id):
            logger.info(f"get_bot({bot_id}) succeeded")
            return bot_dto.to_dict()

    logger.warning(f"get_bot({bot_id}) forbidden for user_id={user_id} (bot owner={bot_dto.user_account_id})")
    raise ApiError(
        f"You don't have rights to get bot {bot_id}. "
        f"bot_dto.user_account_id{bot_dto.user_account_id} user_id{user_id}",
        status_code=403,
    )


@router.put("/{bot_id:int}", dependencies=[Depends(require_json_content_type)])
@with_db_session
def update_bot_admin(bot_id: int, body: BotUpdateRequest, claims: dict = Depends(admin_or_user)):
    """Met à jour un bot existant"""
    logger.info(f"PUT /bot/{bot_id} - update_bot_admin called")
    user_id = claims["sub"]
    user: User = User.query.filter_by(id=user_id).first()
    if not user:
        logger.warning(f"update_bot_admin({bot_id}) rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    if not _can_modify_bot(user, bot_id):
        logger.warning(f"update_bot_admin({bot_id}) forbidden for user_id={user_id}")
        raise ApiError(f"You don't have rights to update bot {bot_id}.", status_code=403)

    validated_data = body.model_dump(exclude_unset=True)
    bot_dto: BotDto = bot_svc.update(bot_id, validated_data)
    if not bot_dto:
        logger.warning(f"update_bot_admin({bot_id}) not found")
        raise ApiError("Bot not found", status_code=404)

    logger.info(f"update_bot_admin({bot_id}) succeeded")
    return bot_dto.to_dict()


@router.delete("/{bot_id:int}", status_code=204, dependencies=[Depends(admin_or_user)])
@with_db_session
def delete_bot(bot_id: int, claims: dict = Depends(admin_or_user)):
    """Supprime un bot"""
    logger.info(f"DELETE /bot/{bot_id} - delete_bot called")
    user_id = claims["sub"]
    user: User = User.query.filter_by(id=user_id).first()
    if not user:
        logger.warning(f"delete_bot({bot_id}) rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    if not _can_modify_bot(user, bot_id):
        logger.warning(f"delete_bot({bot_id}) forbidden for user_id={user_id}")
        raise ApiError(f"You don't have rights to delete bot {bot_id}", status_code=403)

    if not bot_svc.delete(bot_id):
        logger.warning(f"delete_bot({bot_id}) not found")
        raise ApiError("Bot not found", status_code=404)

    logger.info(f"delete_bot({bot_id}) succeeded")
    return Response(status_code=204)
