"""Small assertion/utility helpers shared across the HTTP regression suite."""

import json
import uuid


def unique(prefix: str) -> str:
    """A short random suffix so unique DB columns (mail, name) never collide
    between test runs, including concurrent/repeated ones against a live DB."""
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def assert_error(response, status_code: int, substring: str | None = None) -> dict:
    """Asserts the app's standard {"error": "..."} response shape."""
    assert response.status_code == status_code, response.text
    body = response.json()
    assert "error" in body, body
    if substring:
        assert substring.lower() in body["error"].lower(), body["error"]
    return body


def read_sse(response) -> str:
    """Accumulates the `answer` field of each SSE chunk emitted by
    rest_rag.py's streaming endpoints (ask_with_stream's `generate()`
    yields `data: {"answer": "..."}\\n\\n` per chunk, terminated by
    `data: [DONE]` -- this is the app's own event shape, not the raw
    upstream LLM/mock-server chunk format)."""
    text = ""
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        chunk = json.loads(payload)
        if isinstance(chunk, dict) and "answer" in chunk:
            text += chunk["answer"] or ""
    return text
