"""Unit tests for BotAssignmentService against in-memory fake repositories:
no server, no MySQL."""

import asyncio
from types import SimpleNamespace

import pytest

from ai_server.config.constant import GUEST_ROLE, USER_ROLE
from ai_server.exceptions.service_exceptions import NotFoundError, ServiceError
from ai_server.models import BotAssignment
from ai_server.services.bot_assignment_svc import BotAssignmentService

PARENT_ID, GUEST_ID, STRANGER_ID = 1, 2, 3


class FakeGetRepository:
    def __init__(self, rows):
        self.rows = rows

    async def get(self, row_id):
        return self.rows.get(row_id)


class FakeBotAssignmentRepository:
    def __init__(self, assignments=()):
        self.rows = list(assignments)
        self.commits = 0

    def add(self, assignment):
        assignment.id = assignment.id or len(self.rows) + 100
        self.rows.append(assignment)

    async def find(self, bot_id, user_id, active_only=False):
        return next(
            (
                a
                for a in self.rows
                if a.bot_id == bot_id
                and a.user_id == user_id
                and (a.is_active or not active_only)
            ),
            None,
        )

    async def delete_for_user(self, user_id):
        self.rows = [a for a in self.rows if a.user_id != user_id]

    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1


def _service(assignments=()):
    bots = {
        10: SimpleNamespace(id=10, user_account_id=PARENT_ID),
        11: SimpleNamespace(id=11, user_account_id=PARENT_ID),
        20: SimpleNamespace(id=20, user_account_id=STRANGER_ID),
    }
    users = {
        GUEST_ID: SimpleNamespace(id=GUEST_ID, roles=GUEST_ROLE, parent_id=PARENT_ID)
    }
    repo = FakeBotAssignmentRepository(assignments)
    return (
        BotAssignmentService(repo, FakeGetRepository(bots), FakeGetRepository(users)),
        repo,
    )


def _assignment(bot_id, is_active=True, assignment_id=1):
    a = BotAssignment(
        bot_id=bot_id, user_id=GUEST_ID, assigned_by=PARENT_ID, is_active=is_active
    )
    a.id = assignment_id
    return a


def test_create_reactivates_existing_assignment():
    svc, repo = _service([_assignment(10, is_active=False)])

    dto = asyncio.run(
        svc.create({"bot_id": 10, "user_id": GUEST_ID, "assigned_by": PARENT_ID})
    )

    assert dto.id == 1 and dto.is_active
    assert len(repo.rows) == 1 and repo.commits == 1


def test_create_rejects_bot_of_another_owner():
    svc, repo = _service()

    with pytest.raises(ServiceError, match="does not belong"):
        asyncio.run(
            svc.create({"bot_id": 20, "user_id": GUEST_ID, "assigned_by": PARENT_ID})
        )
    assert repo.commits == 0


def test_replace_user_assignments_swaps_the_set_without_committing():
    svc, repo = _service([_assignment(10)])

    dtos = asyncio.run(svc.replace_user_assignments(GUEST_ID, PARENT_ID, [11]))

    assert [d.bot_id for d in dtos] == [11]
    assert [a.bot_id for a in repo.rows] == [11]
    assert repo.commits == 0  # the caller owns the transaction


def test_replace_user_assignments_rejects_before_deleting_anything():
    svc, repo = _service([_assignment(10)])

    with pytest.raises(NotFoundError):
        asyncio.run(svc.replace_user_assignments(GUEST_ID, PARENT_ID, [11, 999]))
    assert [a.bot_id for a in repo.rows] == [10]


def test_user_role_target_needs_no_parent_link():
    svc, _repo = _service()
    svc.user_repo.rows[5] = SimpleNamespace(id=5, roles=USER_ROLE, parent_id=-1)

    dtos = asyncio.run(svc.replace_user_assignments(5, PARENT_ID, [10]))

    assert [d.user_id for d in dtos] == [5]
