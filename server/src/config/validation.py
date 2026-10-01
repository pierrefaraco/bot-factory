"""Shared Pydantic validation-error formatting for the standard
{"error": "..."} API error shape.
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
