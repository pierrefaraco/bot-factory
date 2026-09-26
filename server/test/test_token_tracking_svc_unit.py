"""Unit tests for TokenTrackingService against a fake TokenUsageRepository:
no server, no MySQL -- what injecting the repository buys over querying
the session directly from the service."""

import asyncio

import pytest
from sqlalchemy.exc import OperationalError

from ai_server.config.config import app_config
from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dto.user_dto import UserDto
from ai_server.services.token_tracking_svc import TokenTrackingService


class FakeTokenUsageRepository:
    def __init__(self, tokens_by_user=None, fail=False):
        self.tokens_by_user = tokens_by_user or {}
        self.fail = fail
        self.rolled_back = False

    async def sum_total_tokens(self, user_id, since=None):
        if self.fail:
            raise OperationalError("SELECT", {}, Exception("db down"))
        return self.tokens_by_user.get(user_id)

    async def rollback(self):
        self.rolled_back = True


def _user(user_id, roles=USER_ROLE, parent_id=-1):
    return UserDto(user_id, f"{user_id}@x.io", "u", roles, parent_id, True)


@pytest.fixture()
def token_limit(monkeypatch):
    monkeypatch.setattr(app_config, "TOKEN_LIMIT_PER_USER_24H", 1000)


def test_quota_of_guest_is_billed_to_parent(token_limit):
    svc = TokenTrackingService(FakeTokenUsageRepository({7: 1200}))

    quota = asyncio.run(svc.get_token_quota(_user(42, GUEST_ROLE, parent_id=7)))

    assert quota == {
        "billed_user_id": 7,
        "limit_24h": 1000,
        "used_24h": 1200,
        "remaining_24h": 0,
        "exceeded": True,
    }


def test_admin_has_no_quota(token_limit):
    svc = TokenTrackingService(FakeTokenUsageRepository({1: 5000}))

    quota = asyncio.run(svc.get_token_quota(_user(1, ADMIN_ROLE)))

    assert quota["limit_24h"] is None and quota["exceeded"] is False


def test_db_error_reads_as_zero_and_rolls_back():
    repo = FakeTokenUsageRepository(fail=True)
    svc = TokenTrackingService(repo)

    assert asyncio.run(svc.get_user_tokens_last_24h(3)) == 0
    assert repo.rolled_back
