"""Deterministic stand-in for Mistral's chat completions API.

Used only by the HTTP regression suite (server/test/): the real ai-server
container is pointed at this service via the MISTRAL_BASE_URL env var
(docker-compose.test.yml) instead of https://api.mistral.ai/v1, so RAG/chat
endpoints can be tested without a real API key, network access, or
non-deterministic model output.
"""

import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()

CANNED_TEXT = "This is a deterministic mock LLM response."


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()

    if body.get("stream"):

        def generate():
            words = CANNED_TEXT.split(" ")
            for i, word in enumerate(words):
                chunk = {
                    "choices": [
                        {
                            "delta": {
                                "role": "assistant" if i == 0 else None,
                                "content": (" " if i else "") + word,
                            },
                            "finish_reason": None,
                        }
                    ]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            final_chunk = {
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": len(words),
                    "total_tokens": 10 + len(words),
                },
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    return JSONResponse(
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": CANNED_TEXT},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        }
    )


@app.get("/v1/health")
async def health():
    return {"status": "ok"}
