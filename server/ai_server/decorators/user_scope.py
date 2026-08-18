"""Shared per-resource authorization for merged guest/<id> + admin/<id>
routes.

Used after @role_required([ADMIN_ROLE, USER_ROLE]) on a route that takes
a target user id and needs the same "own it or be admin" check that used
to be duplicated across every rest_users_admin.py / rest_token_stats.py
guest-scoped handler.
"""

from http import HTTPStatus
from typing import Optional, Tuple

from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from ai_server.config.constant import ADMIN_ROLE
from ai_server.dao.database import User


def authorize_user_scope(
    target_id: int, allow_self: bool = True
) -> Optional[Tuple]:
    """Returns None if the caller may act on target_id, otherwise a
    (jsonify(...), status_code) tuple to `return` immediately.

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
    caller_id = get_jwt_identity()
    caller = User.query.filter_by(id=caller_id).first()
    if not caller:
        return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

    if allow_self and int(caller_id) == target_id:
        return None

    target = User.query.filter_by(id=target_id).first()
    if not target:
        return jsonify({"error": "Guest user not found"}), HTTPStatus.NOT_FOUND

    # int(target_id) != int(caller_id) here specifically, not just "any
    # Admin target": allow_self=False routes (deactivate/activate) reach
    # this point even when target_id IS the caller's own id, and an Admin
    # has always been allowed to self-service those (that's what
    # allow_self=False was gating for non-admins in the first place, via
    # the parent_id check below -- it was never meant to touch this case).
    if target.roles == ADMIN_ROLE and int(target_id) != int(caller_id):
        return jsonify(
            {"error": f"Unable to act on user {target_id} - target is an Admin"}
        ), HTTPStatus.FORBIDDEN

    if caller.roles == ADMIN_ROLE:
        return None

    if target.parent_id == int(caller_id):
        return None

    return jsonify(
        {"error": f"Unable to access user {target_id} - not your guest"}
    ), HTTPStatus.FORBIDDEN
