"""Shared per-resource authorization for merged guest/<id> + admin/<id>
routes.

Used after a role check on a route that takes a target user id and needs
the same "own it or be admin" check that used to be duplicated across
every rest_users_admin.py / rest_token_stats.py guest-scoped handler.

caller_id is passed in rather than read off any framework's own request
context, so this is usable from a plain function call regardless of
what's calling it.
"""

from http import HTTPStatus
from typing import Optional, Tuple

from ai_server.config.constant import ADMIN_ROLE
from ai_server.dao.database import User


def authorize_user_scope(
    caller_id, target_id: int, allow_self: bool = True
) -> Optional[Tuple[dict, HTTPStatus]]:
    """Returns None if the caller may act on target_id, otherwise a
    ({"error": ...}, status_code) tuple for the caller to turn into an
    error response.

    - allow_self and target_id is the caller's own id: allowed (including
      an Admin acting on themselves).
    - target_id belongs to another Admin: always 403, even for an Admin
      caller -- peer admin accounts are out of scope for this whole route
      family (role change, delete, activate/deactivate, bot assignment...).
    - ADMIN (any other target): unrestricted.
    - USER: allowed only if target_id is one of their guests
      (target.parent_id == caller_id).
    - Anything else: 403.
    """
    caller = User.query.filter_by(id=caller_id).first()
    if not caller:
        return {"error": "User not found"}, HTTPStatus.UNAUTHORIZED

    if allow_self and int(caller_id) == target_id:
        return None

    target = User.query.filter_by(id=target_id).first()
    if not target:
        return {"error": "Guest user not found"}, HTTPStatus.NOT_FOUND

    # int(target_id) != int(caller_id) here specifically, not just "any
    # Admin target": allow_self=False routes (deactivate/activate) reach
    # this point even when target_id IS the caller's own id, and an Admin
    # has always been allowed to self-service those (that's what
    # allow_self=False was gating for non-admins in the first place, via
    # the parent_id check below -- it was never meant to touch this case).
    if target.roles == ADMIN_ROLE and int(target_id) != int(caller_id):
        return (
            {"error": f"Unable to act on user {target_id} - target is an Admin"},
            HTTPStatus.FORBIDDEN,
        )

    if caller.roles == ADMIN_ROLE:
        return None

    if target.parent_id == int(caller_id):
        return None

    return (
        {"error": f"Unable to access user {target_id} - not your guest"},
        HTTPStatus.FORBIDDEN,
    )
