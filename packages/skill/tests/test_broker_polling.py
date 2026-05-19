"""Broker polling cursor behavior."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from hearme_skill.broker import BrokerClient
from hearme_skill.ledger import Ledger


@pytest.fixture
async def open_ledger(tmp_root):
    led = Ledger(tmp_root / "ledger.sqlite")
    await led.open()
    yield led
    await led.close()


async def test_poll_cursor_uses_latest_broker_created_at(open_ledger):
    first = "2026-05-19T10:00:00Z"
    second = "2026-05-19T10:00:05Z"
    seen_params: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.append(request.url.params.get("since"))
        return httpx.Response(
            200,
            json=[
                {
                    "question_id": "00000000-0000-0000-0000-000000000001",
                    "text": "first?",
                    "topic": "coffee",
                    "created_at": first,
                    "closes_at": "2026-05-20T10:00:00Z",
                    "nonce": "nonce-1",
                },
                {
                    "question_id": "00000000-0000-0000-0000-000000000002",
                    "text": "second?",
                    "topic": "coffee",
                    "created_at": second,
                    "closes_at": "2026-05-20T10:00:00Z",
                    "nonce": "nonce-2",
                },
            ],
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        broker = BrokerClient(
            base_url="http://broker.test",
            client=client,
            ledger=open_ledger,
        )
        questions = await broker.poll_questions()

    assert [q.created_at for q in questions] == [
        datetime(2026, 5, 19, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 19, 10, 0, 5, tzinfo=timezone.utc),
    ]
    assert await open_ledger.last_seen_cursor() == "2026-05-19T10:00:05+00:00"
    assert seen_params == [None]


async def test_poll_cursor_does_not_advance_on_empty_response(open_ledger):
    await open_ledger.set_last_seen("2026-05-19T10:00:05+00:00")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        broker = BrokerClient(
            base_url="http://broker.test",
            client=client,
            ledger=open_ledger,
        )
        questions = await broker.poll_questions()

    assert questions == []
    assert await open_ledger.last_seen_cursor() == "2026-05-19T10:00:05+00:00"
