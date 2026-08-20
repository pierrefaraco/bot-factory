"""FastAPI replacements for Flask's `request.is_json`-based Content-Type
checks. FastAPI/Starlette parses a Pydantic body parameter from the raw
request bytes regardless of the Content-Type header -- Flask's
`request.get_json()` (and SpecTree's automatic `@api.validate(json=...)`
gate, which relies on it) does not: a Content-Type that isn't
"application/json" (or a "+json" suffix) makes it treat the body as
absent, 400 status.

Two different shapes of that behavior show up across the Flask
blueprints, so there are two dependencies here:

- require_json_content_type: for a blueprint with an unconditional
  `@bp.before_request` Content-Type guard (rest_bot.py, rest_authent.py)
  that runs before SpecTree/the handler either way -- always the same
  "Content-Type must be application/json" message.

- require_json_body(model_cls): for a blueprint with no such hook
  (rest_avatar.py, ...), where a wrong Content-Type only ever surfaces
  through SpecTree's model validation treating the body as absent. If
  model_cls has any required field, validating {} against it 400s with
  the same pydantic "Field required" message SpecTree produced. If every
  field is optional (a PATCH-style model), {} validates fine and nothing
  would otherwise catch a wrong Content-Type -- which is exactly why
  those Flask handlers also carried their own explicit
  `if not request.is_json` check; this falls through to the same
  explicit "Content-Type must be application/json" message for that case.
"""

from typing import Type

from fastapi import Request
from pydantic import BaseModel, ValidationError

from ai_server.config.validation import pydantic_error_messages
from ai_server.exceptions.api_error import ApiError


def _is_json_content_type(request: Request) -> bool:
    mimetype = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or mimetype.endswith("+json")


def require_json_content_type(request: Request) -> None:
    if not _is_json_content_type(request):
        raise ApiError("Content-Type must be application/json", status_code=400)


def require_json_body(model_cls: Type[BaseModel]):
    def dependency(request: Request) -> None:
        if _is_json_content_type(request):
            return
        try:
            model_cls.model_validate({})
        except ValidationError as exc:
            raise ApiError(pydantic_error_messages(exc), status_code=400) from exc
        raise ApiError("Content-Type must be application/json", status_code=400)

    return dependency
