"""Shared fixtures for the HTTP regression suite.

These tests talk to a running ai-server instance over real HTTP (not Flask's
test_client), so the exact same suite can later validate the FastAPI
rewrite by pointing TEST_API_BASE_URL at the new server. Each test creates
its own MySQL rows via a plain SQLAlchemy session (independent of Flask's
app-bound Flask-SQLAlchemy session) and cleans them up afterwards.
"""

import os

import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Makes fixtures defined in factories.py (create_user, create_bot, ...)
# available to every test file, the same way conftest.py fixtures are.
pytest_plugins = ["test.factories"]

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "mysql+pymysql://botcraft_user:123456789@localhost:3306/botcraft?charset=utf8mb4",
)
API_BASE_URL = os.environ.get("TEST_API_BASE_URL", "http://localhost:4444/api")

# READ COMMITTED, not MySQL's REPEATABLE-READ default: this session runs
# alongside the ai-server process's own connection, and a test frequently
# needs to read rows the app just committed via HTTP (e.g. to look up an id
# the response didn't return). Under REPEATABLE-READ, once this session has
# run any query its snapshot is fixed and later app-side commits stay
# invisible to it until a fresh transaction begins on the next commit/query
# boundary — READ COMMITTED avoids that class of flaky "not found" reads.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, isolation_level="READ COMMITTED")
SessionLocal = sessionmaker(bind=engine)


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def api_base_url():
    return API_BASE_URL


@pytest.fixture()
def http_client():
    with requests.Session() as session:
        yield session


@pytest.fixture()
def login(http_client, api_base_url):
    """Hits the real /auth/login endpoint to mint a JWT, so tests exercise
    the actual auth flow instead of hand-crafting tokens."""

    def _login(email: str, password: str) -> dict:
        response = http_client.post(
            f"{api_base_url}/auth/login",
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    return _login
