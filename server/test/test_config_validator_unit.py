import secrets
from pathlib import Path

import pytest

from src.config.validator import KNOWN_PLACEHOLDER_SECRETS, ConfigValidator

REPO_ROOT = Path(__file__).resolve().parents[2]
# Absent from the test-runner image, which only ships server/: skipped there.
ENV_EXAMPLES = [
    path
    for path in (REPO_ROOT / ".env.example", REPO_ROOT / "server" / ".env.example")
    if path.exists()
]


def _env_values(path: Path, key: str) -> list:
    values = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            values.append(line.split("=", 1)[1].strip().strip('"'))
    return values


@pytest.mark.parametrize("path", ENV_EXAMPLES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
@pytest.mark.parametrize("key", ["JWT_SECRET_KEY", "SUPER_ADMIN_PASSWORD"])
def test_env_example_secrets_are_rejected(path, key):
    for value in _env_values(path, key):
        assert not value or value in KNOWN_PLACEHOLDER_SECRETS


@pytest.mark.parametrize(
    "secret", ["", "short", "your-secret-key-change-in-production"]
)
def test_jwt_secret_rejected(secret):
    assert ConfigValidator.jwt_errors(secret)


def test_jwt_secret_accepted():
    assert ConfigValidator.jwt_errors(secrets.token_urlsafe(48)) == []


@pytest.mark.parametrize("password", ["", "123", "change-me", "elevenchars"])
def test_super_admin_password_rejected(password):
    assert ConfigValidator.super_admin_password_errors(password)


def test_raise_if_any():
    ConfigValidator.raise_if_any([])
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        ConfigValidator.raise_if_any(ConfigValidator.jwt_errors(""))
