import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage

from src.services.llm_svc import TokenCountingCallback


def test_records_input_tokens_as_prompt_tokens_and_the_model_used():
    tracking = MagicMock(record_token_usage=AsyncMock())
    users = MagicMock(
        get_user_dto_by_id=AsyncMock(return_value=SimpleNamespace(id=1, parent_id=-1))
    )
    callback = TokenCountingCallback(tracking, users, user_id=1, bot_id=2)
    message = AIMessage(
        content="hi",
        usage_metadata={"input_tokens": 100, "output_tokens": 7, "total_tokens": 107},
        response_metadata={"model": "mistral-small-latest"},
    )
    response = SimpleNamespace(
        generations=[[SimpleNamespace(generation_info={}, message=message)]]
    )

    asyncio.run(callback.on_llm_end(response))

    kwargs = tracking.record_token_usage.await_args.kwargs
    assert (kwargs["prompt_tokens"], kwargs["completion_tokens"]) == (100, 7)
    assert kwargs["total_tokens"] == 107
    assert kwargs["model_name"] == "mistral-small-latest"
