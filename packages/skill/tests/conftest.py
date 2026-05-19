"""Shared test fixtures.

Per ARCHITECTURE.md §12 no test in this suite makes a live LLM or HTTP call.
All external collaborators are doubles defined here or in the package's
`memory/` and `llm/` modules.
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from hearme_skill.crypto.canonical import canonical_json_bytes
from hearme_skill.crypto.ed25519 import Keypair, generate_keypair, sign
from hearme_skill.models import DelegationToken, Question


@pytest.fixture
def phone_keypair() -> Keypair:
    return generate_keypair()


@pytest.fixture
def agent_keypair() -> Keypair:
    return generate_keypair()


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fresh_token(phone_keypair: Keypair, agent_keypair: Keypair, now: datetime) -> DelegationToken:
    """A freshly-issued DelegationToken signed by the test phone key."""

    unsigned = {
        "version": 1,
        "zkpassport_proof": base64.b64encode(b"stub-proof").decode("ascii"),
        "domain": "hearme.network",
        "scope": "v1",
        "unique_identifier": base64.b64encode(b"u" * 32).decode("ascii"),
        "disclosed_predicates": {"age_band": "25-34", "region": "EU"},
        "agent_key": base64.b64encode(agent_keypair.public_bytes).decode("ascii"),
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(days=90)).isoformat().replace("+00:00", "Z"),
    }
    sig = sign(phone_keypair, canonical_json_bytes(unsigned))
    unsigned["phone_signature"] = base64.b64encode(sig).decode("ascii")
    return DelegationToken.model_validate(unsigned)


@pytest.fixture
def expired_token(phone_keypair: Keypair, agent_keypair: Keypair, now: datetime) -> DelegationToken:
    past = now - timedelta(days=100)
    unsigned = {
        "version": 1,
        "zkpassport_proof": base64.b64encode(b"stub-proof").decode("ascii"),
        "domain": "hearme.network",
        "scope": "v1",
        "unique_identifier": base64.b64encode(b"u" * 32).decode("ascii"),
        "disclosed_predicates": {"age_band": "25-34", "region": "EU"},
        "agent_key": base64.b64encode(agent_keypair.public_bytes).decode("ascii"),
        "issued_at": (past - timedelta(days=90)).isoformat().replace("+00:00", "Z"),
        "expires_at": past.isoformat().replace("+00:00", "Z"),
    }
    sig = sign(phone_keypair, canonical_json_bytes(unsigned))
    unsigned["phone_signature"] = base64.b64encode(sig).decode("ascii")
    return DelegationToken.model_validate(unsigned)


@pytest.fixture
def question() -> Question:
    return Question(
        question_id=str(uuid.uuid4()),
        text="Do you prefer single-origin or blends?",
        topic="coffee",
        created_at=datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc),
        closes_at=datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc),
        nonce=base64.b64encode(b"n" * 16).decode("ascii"),
    )


class CountingPhoneBridge:
    """Records every call. The 'phone' shouldn't be called in steady state."""

    def __init__(self) -> None:
        self.call_count = 0
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def __getattr__(self, name: str) -> Any:
        def _record(*args: Any, **kwargs: Any) -> Any:
            self.call_count += 1
            self.calls.append((name, args))
            raise AssertionError(
                f"phone bridge was contacted in steady state: {name}({args!r})"
            )

        return _record


@pytest.fixture
def phone_bridge() -> CountingPhoneBridge:
    return CountingPhoneBridge()


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    """Isolated `~/.hermes/hearme` for each test."""

    root = tmp_path / "hermes" / "hearme"
    root.mkdir(parents=True, exist_ok=True)
    return root
