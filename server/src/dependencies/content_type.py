"""Content-Type checks for JSON routes. FastAPI parses a Pydantic body from
the raw bytes whatever the Content-Type header says; these dependencies
make the API answer 400 on a non-JSON Content-Type instead.

- require_json_content_type: unconditional check, always the same
  "Content-Type must be application/json" message.

- require_json_body(model_cls): if model_cls has a required field, a
  wrong Content-Type is answered like an absent body ("Field required");
  if every field is optional (PATCH-style models), with the explicit
  "Content-Type must be application/json" message.
"""

from typing import Type

from fastapi import Request
from pydantic import BaseModel, ValidationError

from src.config.validation import pydantic_error_messages
from src.exceptions.api_error import ApiError


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
