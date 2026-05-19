"""§1.13 + §12: phone bridge receives ZERO calls across 100 simulated answers.

In steady state, the only outbound contact the skill makes is to the broker.
The phone is touched at install + refresh + revoke — never inside the
answer loop. We drive 100 questions through the full pipeline (memory →
persona → answerer → envelope → submission) and verify the phone-bridge
mock recorded no calls.
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from hearme_skill import answerer as answerer_mod
from hearme_skill import persona as persona_mod
from hearme_skill.broker import BrokerClient
from hearme_skill.delegation import store_delegation
from hearme_skill.envelope import build_envelope
from hearme_skill.ledger import Ledger
from hearme_skill.llm.client import FakeLLMClient
from hearme_skill.memory.mem0_stub import Mem0StubProvider
from hearme_skill.models import Question


def _make_question(idx: int) -> Question:
    return Question(
        question_id=str(uuid.uuid4()),
        text=f"question {idx}: pour-over or espresso?",
        topic="coffee",
        created_at=datetime(2026, 5, 19, tzinfo=timezone.utc) + timedelta(seconds=idx),
        closes_at=datetime(2026, 5, 20, tzinfo=timezone.utc),
        nonce=base64.b64encode(idx.to_bytes(16, "big")).decode("ascii"),
    )


@pytest.fixture
async def open_ledger(tmp_root):
    led = Ledger(tmp_root / "ledger.sqlite")
    await led.open()
    yield led
    await led.close()


async def test_one_hundred_answers_zero_phone_contact(
    tmp_root, fresh_token, agent_keypair, phone_bridge, open_ledger
):
    # Persist the (already-valid) delegation token to disk; this is the same
    # path the real Envelope layer reads from. No phone involved.
    store_delegation(tmp_root / "delegation.token", fresh_token)

    memory = Mem0StubProvider()
    llm = FakeLLMClient()

    posted_envelopes: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/envelopes":
            posted_envelopes.append(request.url.path)
            return httpx.Response(200, json={"accepted": True})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        broker = BrokerClient(
            base_url="http://broker.test", client=client, ledger=open_ledger
        )

        for i in range(100):
            q = _make_question(i)
            persona = persona_mod.project(q, memory)
            ans = answerer_mod.answer(persona, q, llm)
            env = build_envelope(
                question_id=q.question_id,
                answer_text=ans.text,
                nonce=q.nonce,
                delegation_token=fresh_token,
                agent_key=agent_keypair,
            )
            accepted, _reason = await broker.submit_envelope(env)
            assert accepted is True

    # 100 envelopes posted, zero phone contact.
    assert len(posted_envelopes) == 100
    assert phone_bridge.call_count == 0


async def test_steady_state_only_touches_broker(
    tmp_root, fresh_token, agent_keypair, phone_bridge, open_ledger
):
    """Broker is the *only* host the skill talks to in steady state."""

    seen_hosts: set[str] = set()

    def handler(request: httpx.Request) -> httpx.Response:
        seen_hosts.add(request.url.host)
        return httpx.Response(200, json={"accepted": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        broker = BrokerClient(base_url="http://broker.test", client=client, ledger=open_ledger)
        for i in range(5):
            q = _make_question(i)
            env = build_envelope(
                question_id=q.question_id,
                answer_text="x",
                nonce=q.nonce,
                delegation_token=fresh_token,
                agent_key=agent_keypair,
            )
            await broker.submit_envelope(env)

    assert seen_hosts == {"broker.test"}, f"unexpected hosts contacted: {seen_hosts}"
    assert phone_bridge.call_count == 0
