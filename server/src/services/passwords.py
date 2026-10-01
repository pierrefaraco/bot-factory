"""Password hashing: Argon2id (argon2-cffi) for every new hash.

Hashes written before by Werkzeug ("scrypt:n:r:p$salt$hex" or
"pbkdf2:algo:iterations$salt$hex") are still verified, with hashlib, and
needs_rehash() flags them so a successful login upgrades them to Argon2id.

All of these are deliberately CPU-heavy: call them through
run_in_threadpool from async code.
"""

import hashlib
import hmac

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_argon2 = PasswordHasher()

_LEGACY_PREFIXES = ("scrypt:", "pbkdf2:")


def hash_password(password: str) -> str:
    return _argon2.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    if password_hash.startswith(_LEGACY_PREFIXES):
        return _verify_werkzeug(password_hash, password)
    try:
        return _argon2.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    if password_hash.startswith(_LEGACY_PREFIXES):
        return True
    return _argon2.check_needs_rehash(password_hash)


def _verify_werkzeug(password_hash: str, password: str) -> bool:
    try:
        method, salt, expected = password_hash.split("$", 2)
        name, *args = method.split(":")
        salt_bytes, password_bytes = salt.encode(), password.encode()
        if name == "scrypt":
            n, r, p = map(int, args) if args else (2**15, 8, 1)
            actual = hashlib.scrypt(
                password_bytes, salt=salt_bytes, n=n, r=r, p=p, maxmem=132 * n * r * p
            )
        elif name == "pbkdf2" and len(args) == 2:
            actual = hashlib.pbkdf2_hmac(args[0], password_bytes, salt_bytes, int(args[1]))
        else:
            return False
    except ValueError:
        return False
    return hmac.compare_digest(actual.hex(), expected)
