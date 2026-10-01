"""Prints a one-time login link for an existing account.

    python -m src.scripts.create_magic_link <email> [ttl_hours]

Run where the api runs (it needs DATABASE_URL and PUBLIC_URL), e.g. through
`make magic-link EMAIL=...`, which execs it in the api container. Same
service as POST /api/auth/magic-links, minus the need for an admin JWT.
"""

import asyncio
import sys

from src.config.config import AppConfig
from src.database.session import _get_async_engine, async_db_session_scope
from src.exceptions.service_exceptions import AuthenticationError, NotFoundError
from src.repositories import MagicLinkRepository, UserRepository
from src.services.magic_link_svc import DEFAULT_TTL_HOURS, MAX_TTL_HOURS, MagicLinkService


async def main(email: str, ttl_hours: int) -> int:
    svc = MagicLinkService(MagicLinkRepository(), UserRepository())
    try:
        async with async_db_session_scope():
            token, expires_at = await svc.create(email, ttl_hours)
    except NotFoundError:
        print(f"No account with email {email}", file=sys.stderr)
        return 1
    except AuthenticationError:
        print(f"Account {email} is deactivated", file=sys.stderr)
        return 1
    finally:
        # Closes the pool's connections while the event loop still runs,
        # instead of leaving them to be garbage-collected after it.
        await _get_async_engine().dispose()
    print(f"{AppConfig.PUBLIC_URL}/auth?token={token}")
    print(f"Single use, expires {expires_at:%Y-%m-%d %H:%M} UTC", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        sys.exit(2)
    ttl = int(sys.argv[2]) if len(sys.argv) == 3 else DEFAULT_TTL_HOURS
    if not 1 <= ttl <= MAX_TTL_HOURS:
        print(f"ttl_hours must be between 1 and {MAX_TTL_HOURS}", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1], ttl)))
