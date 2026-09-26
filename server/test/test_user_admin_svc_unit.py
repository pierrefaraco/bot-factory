"""Unit tests for UserAdminService.authorize_user_scope() -- the shared
"own it or be admin" rule of every /users/<id> and /token-stats/.../<id>
route -- against an in-memory fake UserRepository: no server, no MySQL."""

import asyncio
from types import SimpleNamespace

import pytest

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.exceptions.api_error import ApiError
from ai_server.services.user_admin_svc import UserAdminService

ADMIN, OTHER_ADMIN, PARENT, GUEST, OTHER_GUEST = 1, 2, 3, 4, 5


class FakeUserRepository:
    def __init__(self, users):
        self.users = {u.id: u for u in users}

    async def get(self, user_id):
        return self.users.get(user_id)


def _service():
    users = [
        SimpleNamespace(id=ADMIN, roles=ADMIN_ROLE, parent_id=-1),
        SimpleNamespace(id=OTHER_ADMIN, roles=ADMIN_ROLE, parent_id=-1),
        SimpleNamespace(id=PARENT, roles=USER_ROLE, parent_id=-1),
        SimpleNamespace(id=GUEST, roles=GUEST_ROLE, parent_id=PARENT),
        SimpleNamespace(id=OTHER_GUEST, roles=GUEST_ROLE, parent_id=99),
    ]
    return UserAdminService(None, FakeUserRepository(users), None, None, None, None)


def _authorize(caller, target, allow_self=True):
    # caller ids come from JWT claims, i.e. as strings
    return asyncio.run(
        _service().authorize_user_scope(str(caller), target, allow_self=allow_self)
    )


@pytest.mark.parametrize(
    "caller, target, allow_self",
    [
        (PARENT, PARENT, True),  # self
        (ADMIN, ADMIN, False),  # an Admin may (de)activate itself
        (PARENT, GUEST, True),  # own guest
        (ADMIN, GUEST, True),  # Admin: any non-Admin target
    ],
)
def test_allowed(caller, target, allow_self):
    assert _authorize(caller, target, allow_self) is None


@pytest.mark.parametrize(
    "caller, target, allow_self, status, message",
    [
        (PARENT, OTHER_GUEST, True, 403, "not your guest"),
        (PARENT, PARENT, False, 403, "not your guest"),
        (ADMIN, OTHER_ADMIN, True, 403, "target is an Admin"),
        (PARENT, 404, True, 404, "Guest user not found"),
        (404, PARENT, True, 401, "User not found"),
    ],
)
def test_rejected(caller, target, allow_self, status, message):
    with pytest.raises(ApiError) as exc_info:
        _authorize(caller, target, allow_self)
    assert exc_info.value.status_code == status
    assert message in exc_info.value.data["error"]
