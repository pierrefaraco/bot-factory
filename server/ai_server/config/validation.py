"""Shared Pydantic validation-error formatting for the standard
{"error": "..."} API error shape used across every native FastAPI route.

(Used to also hold the SpecTree setup for Flask's now-retired
@api.validate(...) blueprints -- self-hosted Swagger UI and all, since
SpecTree's Flask integration needs a real Flask app to attach routes to,
which no longer exists anywhere in this process.)
"""

from pydantic import ValidationError


def pydantic_error_messages(exc: ValidationError) -> str:
    """Human-readable message for a Pydantic validation failure, for the
    standard {"error": "..."} API error shape."""
    errors = exc.errors(include_url=False, include_context=False, include_input=False)
    parts = []
    for err in errors:
        loc = ".".join(str(part) for part in err.get("loc", ()))
        parts.append(f"{loc}: {err['msg']}" if loc else err["msg"])
    return "; ".join(parts)
