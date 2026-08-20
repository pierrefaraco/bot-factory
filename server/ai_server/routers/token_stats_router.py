"""Token Statistics REST API -- native FastAPI port of the former
ai_server/rest/rest_token_stats.py Flask blueprint (Phase 1 of the
Flask -> FastAPI migration). Same URLs, same response shapes, same role
checks; unhandled exceptions fall through to asgi.py's catch-all 500
handler instead of each function repeating its own try/except.

Query validation note: the original endpoints declared a
TokenHistoryQuery(limit, last24h) SpecTree/Pydantic model for docs, but
then re-parsed request.args by hand instead of using the validated
values -- and did so inconsistently between the two /history/* routes:
`/history/me` compared the raw string against "true", while
`/history/user/<id>` used Werkzeug's `type=bool` (Python's `bool("false")
is True`, so any non-empty value there was truthy). This port uses one
consistent, correctly-parsed `last24h: bool` query param for both routes
via FastAPI/Pydantic -- flagging this as a deliberate behavior fix, not a
silent change: the Werkzeug `type=bool` reading was very likely an
unintentional bug, not a documented contract.
"""

from fastapi import APIRouter, Depends, Query

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.decorators.user_scope import authorize_user_scope
from ai_server.dependencies.auth import require_roles
from ai_server.dependencies.db_session import with_db_session
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.token_tracking_svc import TokenTrackingService

router = APIRouter(prefix="/api/token-stats", tags=["token-stats"])

logger = BotFactoryLogger()
token_tracking_svc = TokenTrackingService()

any_role = require_roles([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
admin_or_user = require_roles([ADMIN_ROLE, USER_ROLE])
admin_only = require_roles([ADMIN_ROLE])


def _enforce_user_scope(caller_id, target_id: int, allow_self: bool = True) -> None:
    """authorize_user_scope() returns a ({"error": ...}, status_code)
    tuple on rejection (shared with users_admin_router.py) -- convert
    that into ApiError here."""
    error = authorize_user_scope(caller_id, target_id, allow_self=allow_self)
    if error:
        response, status_code = error
        raise ApiError(response["error"], status_code=status_code)


@router.get("/me")
@with_db_session
def get_token_stats_self(claims: dict = Depends(any_role)):
    """Get token statistics for the current user"""
    user_id = claims["sub"]
    logger.info("GET /token-stats/me - get_token_stats_self called")
    stats = token_tracking_svc.get_user_token_stats(user_id)
    logger.info(f"get_token_stats_self succeeded for user_id={user_id}")
    return stats


@router.get("/user/{user_id}")
@with_db_session
def get_token_stats_by_id(user_id: int, claims: dict = Depends(admin_or_user)):
    """Get token statistics for a user (own guest, or any user if admin)"""
    logger.info(f"GET /token-stats/user/{user_id} - get_token_stats_by_id called")
    _enforce_user_scope(claims["sub"], user_id)
    stats = token_tracking_svc.get_user_token_stats(user_id)
    logger.info(f"get_token_stats_by_id({user_id}) succeeded")
    return stats


@router.get("/history/me")
@with_db_session
def get_token_history_self(
    claims: dict = Depends(any_role),
    limit: int = Query(default=100, ge=1, le=1000),
    last24h: bool = Query(default=False),
):
    """Get token usage history for the current user"""
    user_id = claims["sub"]
    logger.debug(f"get_token_history_self({user_id}) params: limit={limit} last24h={last24h}")
    history = token_tracking_svc.get_user_token_history(user_id, limit, last24h)
    logger.info(f"get_token_history_self({user_id}) succeeded count={len(history)}")
    return {"history": history}


@router.get("/history/user/{user_id}")
@with_db_session
def get_token_history_by_id(
    user_id: int,
    claims: dict = Depends(admin_or_user),
    limit: int = Query(default=100, ge=1, le=1000),
    last24h: bool = Query(default=False),
):
    """Get token usage history for a user (own guest, or any user if admin)"""
    logger.info(f"GET /token-stats/history/user/{user_id} - get_token_history_by_id called")
    _enforce_user_scope(claims["sub"], user_id)
    logger.debug(f"get_token_history_by_id({user_id}) params: limit={limit} last24h={last24h}")
    history = token_tracking_svc.get_user_token_history(user_id, limit, last24h)
    logger.info(f"get_token_history_by_id({user_id}) succeeded count={len(history)}")
    return {"history": history}


@router.get("/bot/{bot_id}", dependencies=[Depends(admin_or_user)])
@with_db_session
def get_bot_token_stats(bot_id: int):
    """Get token statistics for a specific bot"""
    logger.info(f"GET /token-stats/bot/{bot_id} - get_bot_token_stats called")
    stats = token_tracking_svc.get_bot_token_stats(bot_id)
    logger.info(f"get_bot_token_stats({bot_id}) succeeded")
    return stats


@router.get("/all-users", dependencies=[Depends(admin_only)])
@with_db_session
def get_all_users_token_stats():
    """Get token statistics for all users (admin only)"""
    logger.info("GET /token-stats/all-users - get_all_users_token_stats called")
    stats = token_tracking_svc.get_all_users_token_stats()
    logger.info(f"get_all_users_token_stats succeeded count={len(stats)}")
    return {"users": stats}


@router.get("/total/me")
@with_db_session
def get_total_tokens_self(claims: dict = Depends(any_role)):
    """Get total tokens consumed by the current user"""
    user_id = claims["sub"]
    logger.info("GET /token-stats/total/me - get_total_tokens_self called")
    total = token_tracking_svc.get_user_total_tokens(user_id)
    logger.info(f"get_total_tokens_self({user_id}) succeeded")
    return {"user_id": user_id, "total_tokens": total}


@router.get("/total/user/{user_id}")
@with_db_session
def get_total_tokens_by_id(user_id: int, claims: dict = Depends(admin_or_user)):
    """Get total tokens consumed by a user (own guest, or any user if admin)"""
    logger.info(f"GET /token-stats/total/user/{user_id} - get_total_tokens_by_id called")
    _enforce_user_scope(claims["sub"], user_id)
    total = token_tracking_svc.get_user_total_tokens(user_id)
    logger.info(f"get_total_tokens_by_id({user_id}) succeeded")
    return {"user_id": user_id, "total_tokens": total}


@router.get("/last-24h/me")
@with_db_session
def get_tokens_last_24h_self(claims: dict = Depends(any_role)):
    """Get total tokens consumed by the current user in the last 24 hours"""
    user_id = claims["sub"]
    logger.info("GET /token-stats/last-24h/me - get_tokens_last_24h_self called")
    total = token_tracking_svc.get_user_tokens_last_24h(user_id)
    logger.info(f"get_tokens_last_24h_self({user_id}) succeeded")
    return {"user_id": user_id, "total_tokens_last_24h": total}


@router.get("/last-24h/user/{user_id}")
@with_db_session
def get_tokens_last_24h_by_id(user_id: int, claims: dict = Depends(admin_or_user)):
    """Get total tokens consumed by a user in the last 24h (own guest, or
    any user if admin)"""
    logger.info(f"GET /token-stats/last-24h/user/{user_id} - get_tokens_last_24h_by_id called")
    _enforce_user_scope(claims["sub"], user_id)
    total = token_tracking_svc.get_user_tokens_last_24h(user_id)
    logger.info(f"get_tokens_last_24h_by_id({user_id}) succeeded")
    return {"user_id": user_id, "total_tokens_last_24h": total}


@router.get("/stats-24h/me")
@with_db_session
def get_stats_last_24h_self(claims: dict = Depends(any_role)):
    """Get detailed token statistics for the current user in the last 24 hours"""
    user_id = claims["sub"]
    logger.info("GET /token-stats/stats-24h/me - get_stats_last_24h_self called")
    stats = token_tracking_svc.get_user_stats_last_24h(user_id)
    logger.info(f"get_stats_last_24h_self({user_id}) succeeded")
    return stats


@router.get("/stats-24h/user/{user_id}")
@with_db_session
def get_stats_last_24h_by_id(user_id: int, claims: dict = Depends(admin_or_user)):
    """Get detailed token stats for a user in the last 24h (own guest, or
    any user if admin)"""
    logger.info(f"GET /token-stats/stats-24h/user/{user_id} - get_stats_last_24h_by_id called")
    _enforce_user_scope(claims["sub"], user_id)
    stats = token_tracking_svc.get_user_stats_last_24h(user_id)
    logger.info(f"get_stats_last_24h_by_id({user_id}) succeeded")
    return stats


@router.get("/admin-summary")
@with_db_session
def get_admin_token_usage_summary(claims: dict = Depends(admin_or_user)):
    """Get 24h/30d token totals for every account and guest the caller can
    see in one batch call (for the admin Guest/User tables) -- everyone for
    Admin, only the caller's own account + guests for a User (a guest's
    usage is always recorded under its parent's user_id, so scoping by
    user_id already covers both)."""
    caller_id = claims["sub"]
    scope_user_id = None if ADMIN_ROLE in claims.get("roles", "") else int(caller_id)
    logger.debug(
        f"get_admin_token_usage_summary caller_id={caller_id} scope_user_id={scope_user_id}"
    )
    summary = token_tracking_svc.get_admin_token_usage_summary(scope_user_id)
    logger.info(f"get_admin_token_usage_summary succeeded for caller_id={caller_id}")
    return summary
