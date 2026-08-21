import asyncio
import time

import pytest

from api import chat
from models.schemas import Message


def _messages() -> list[Message]:
    return [Message(role="user", content="Hello")]


def _discard_scheduled(coroutine) -> None:
    coroutine.close()


@pytest.mark.asyncio
async def test_provider_hands_off_after_first_token_timeout(monkeypatch):
    async def delayed_generator(_messages, _session_id):
        await asyncio.sleep(0.2)
        yield "too late"

    monkeypatch.setattr(chat, "schedule", _discard_scheduled)
    started_at = time.perf_counter()

    response = await chat._create_provider_stream(
        "SlowProvider",
        "slow-model",
        delayed_generator,
        _messages(),
        0.01,
        None,
    )

    assert response is None
    assert time.perf_counter() - started_at < 0.15


@pytest.mark.asyncio
async def test_selected_provider_stream_cuts_off_idle_stall(monkeypatch):
    async def stalling_generator(_messages, _session_id):
        yield "first"
        await asyncio.sleep(0.2)
        yield "too late"

    monkeypatch.setattr(chat, "schedule", _discard_scheduled)
    monkeypatch.setattr(chat, "PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS", 0.01)

    response = await chat._create_provider_stream(
        "StallingProvider",
        "stalling-model",
        stalling_generator,
        _messages(),
        0.1,
        None,
    )

    assert response is not None
    chunks = [chunk async for chunk in response.body_iterator]
    assert "".join(chunks) == "first\n\nZero's upstream connection stalled. Try that again."


@pytest.mark.asyncio
async def test_selected_provider_caps_persisted_response(monkeypatch):
    async def oversized_generator(_messages, _session_id):
        yield "a" * 20
        yield "b" * 20

    monkeypatch.setattr(chat, "schedule", _discard_scheduled)
    monkeypatch.setattr(chat, "MAX_ASSISTANT_MESSAGE_CHARS", 25)
    response = await chat._create_provider_stream(
        "LargeProvider", "large-model", oversized_generator, _messages(), 0.1, None,
    )
    assert response is not None
    chunks = [chunk async for chunk in response.body_iterator]
    assert "".join(chunks) == "a" * 20 + "b" * 5
