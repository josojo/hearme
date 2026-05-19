"""Hermes skill entrypoint.

Hermes hosts skills via a small entry-point contract. The actual Hermes API
isn't stable enough at v0 to import here; we expose:

* ``entrypoint(host)`` — the function Hermes calls when loading the skill.
  Adapts the host's channel/memory/LLM to the protocols in this package and
  starts the per-question loop.
* ``cli()`` — local command-line interface for onboarding + dev runs.

The "host" object is whatever Hermes hands us; the README documents the
expected attributes (``memory``, ``llm``, ``channel``, ``node_id``).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Any

import httpx

from . import answerer as answerer_mod
from . import persona as persona_mod
from .broker import BrokerClient
from .config import get_settings
from .crypto.keystore import load_or_create_agent_keypair
from .delegation import (
    DelegationError,
    DelegationExpired,
    DelegationMissing,
    load_usable,
)
from .envelope import build_envelope
from .ledger import Ledger
from .llm.client import LLMClient
from .memory.mem0_stub import Mem0StubProvider
from .memory.provider import MemoryProvider
from .models import Question
from .onboarding import begin_onboarding, render_qr_ascii, accept_delegation_from_mock_phone
from .policy import LedgerStats, decide, load_policy
from .ui import UI, Channel, InMemoryChannel

log = logging.getLogger("hearme_skill")


async def answer_one(
    question: Question,
    *,
    memory: MemoryProvider,
    llm: LLMClient,
    ledger: Ledger,
    broker: BrokerClient,
    ui: UI,
    settings,
) -> str:
    """Process a single question end-to-end. Returns the resulting status string."""

    # §1.9 — replay-safe: never re-submit a question we already answered.
    if await ledger.has_submission(question.question_id):
        return "skip-already-submitted"

    policy = load_policy(settings.policy_path)
    stats = LedgerStats(
        answered_today=await ledger.answered_today(),
        has_active_delegation=settings.delegation_path.exists(),
        already_answered_ids=await ledger.already_answered_ids(),
    )

    decision = decide(question, policy, stats)
    if decision.action == "decline":
        return f"decline:{decision.reason}"

    # Delegation must be loadable + unexpired BEFORE we spend an LLM call.
    try:
        token = load_usable(settings.delegation_path)
    except DelegationExpired:
        await ui.announce_expiry()
        return "decline:delegation-expired"
    except DelegationMissing:
        await ui.channel.notify("Hearme: no DelegationToken. Run onboarding.")
        return "decline:delegation-missing"

    await ui.maybe_nudge_for_refresh(token)

    await ledger.record_question(
        question.question_id,
        question.text,
        question.topic,
        question.closes_at,
        question.nonce,
    )

    projection = persona_mod.project(question, memory)
    # Answerer NEVER receives token / unique_identifier (§1.4, §7.4).
    answer = answerer_mod.answer(projection, question, llm)
    await ledger.record_answer(question.question_id, answer.text, answer.rationale)

    if decision.action == "prompt_user" or policy.auto_submit_window_seconds == 0:
        ok = await ui.preview_and_confirm(
            question, answer, auto_submit_window_seconds=policy.auto_submit_window_seconds
        )
        if not ok:
            return "veto"

    agent_kp = load_or_create_agent_keypair(settings.agent_key_path)
    envelope = build_envelope(
        question_id=question.question_id,
        answer_text=answer.text,  # `.rationale` deliberately NOT passed
        nonce=question.nonce,
        delegation_token=token,
        agent_key=agent_kp,
    )

    accepted, reason = await broker.submit_envelope(envelope)
    # Hash hex for the ledger record.
    from .delegation import hash_of

    dhash_hex = hash_of(token).hex()
    await ledger.record_submission(
        question.question_id,
        delegation_hash_hex=dhash_hex,
        agent_signature_b64=envelope.agent_signature,
        accepted=accepted,
        reason=reason or None,
    )
    return "accepted" if accepted else f"rejected:{reason}"


async def run_loop(host: Any) -> None:
    """Steady-state loop. Polls broker, processes new questions one at a time."""

    settings = get_settings()
    settings.root_dir.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(settings.ledger_path)
    await ledger.open()

    channel: Channel = getattr(host, "channel", None) or InMemoryChannel()
    memory: MemoryProvider = getattr(host, "memory", None) or Mem0StubProvider()
    llm: LLMClient = getattr(host, "llm")  # required from host in production
    ui = UI(channel=channel)

    async with httpx.AsyncClient() as client:
        broker = BrokerClient(
            base_url=settings.broker_url,
            client=client,
            ledger=ledger,
            poll_interval_seconds=settings.poll_interval_seconds,
        )
        try:
            while True:
                questions = await broker.poll_questions()
                for q in questions:
                    try:
                        status = await answer_one(
                            q,
                            memory=memory,
                            llm=llm,
                            ledger=ledger,
                            broker=broker,
                            ui=ui,
                            settings=settings,
                        )
                        log.info("question %s -> %s", q.question_id, status)
                    except DelegationError as exc:
                        log.warning("delegation error: %s", exc)
                    except Exception:  # noqa: BLE001
                        log.exception("question %s failed", q.question_id)
                await asyncio.sleep(settings.poll_interval_seconds)
        finally:
            await ledger.close()


def entrypoint(host: Any) -> None:
    """Hermes entry point — see README for the host contract.

    Hermes calls this synchronously; we kick off the asyncio loop ourselves.
    """

    asyncio.run(run_loop(host))


# --- CLI ------------------------------------------------------------------


def _cmd_onboard(args: argparse.Namespace) -> int:
    settings = get_settings()
    settings.root_dir.mkdir(parents=True, exist_ok=True)
    handoff = begin_onboarding(
        agent_key_path=settings.agent_key_path,
        hermes_node_id=args.node_id,
    )
    print("Scan this QR with the ZKPassport app:\n")
    print(render_qr_ascii(handoff.to_qr_payload()))
    return 0


def _cmd_accept_mock(args: argparse.Namespace) -> int:
    settings = get_settings()
    raw = sys.stdin.read() if args.token_path == "-" else open(args.token_path).read()
    token = accept_delegation_from_mock_phone(
        raw_json=raw, delegation_path=settings.delegation_path
    )
    print(f"Stored delegation token (expires {token.expires_at.isoformat()})")
    return 0


def cli() -> int:
    parser = argparse.ArgumentParser(prog="hearme-skill")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_onboard = sub.add_parser("onboard", help="Generate agent key + print QR")
    p_onboard.add_argument("--node-id", default="hermes-local-0")
    p_onboard.set_defaults(func=_cmd_onboard)

    p_accept = sub.add_parser(
        "accept-mock-delegation",
        help="Accept a DelegationToken from scripts/mock-phone.py",
    )
    p_accept.add_argument("token_path", help="Path to token JSON, or '-' for stdin")
    p_accept.set_defaults(func=_cmd_accept_mock)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(cli())
