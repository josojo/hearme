"""Policy — § 7.2.

Pure function. Reads user policy from YAML at ``~/.hermes/hearme/policy.yaml``.

Per §1.7 ("Indistinguishable response fidelity"), this layer MUST NOT branch
on whether the question is a honeypot. It does not inspect question text for
test markers; it only consults the user's declared topic policy and ledger
stats.

Per §11, payment fields are absent in v0 — `min_payment` is parsed for
forward-compat but never read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .models import Decision, Question


@dataclass(frozen=True)
class LedgerStats:
    """Inputs the Policy layer needs from the local ledger."""

    answered_today: int = 0
    has_active_delegation: bool = True
    already_answered_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class UserPolicy:
    topic_allowlist: frozenset[str] = field(default_factory=frozenset)
    topic_blocklist: frozenset[str] = field(default_factory=frozenset)
    max_answers_per_day: int = 50
    # v0: ignored (no payment field on questions). Carried for forward-compat.
    min_payment: float = 0.0
    auto_submit_window_seconds: int = 0
    # If False, the layer always returns "prompt_user" rather than "answer"
    # — § 1.12 override is sacred.
    auto_answer: bool = False

    @classmethod
    def default(cls) -> "UserPolicy":
        # Hearme defaults to off; opt-in per category (§1.1).
        return cls()


def load_policy(path: Path) -> UserPolicy:
    """Parse YAML policy from disk. Missing file → default (everything off)."""

    if not path.exists():
        return UserPolicy.default()
    raw = yaml.safe_load(path.read_text()) or {}
    return UserPolicy(
        topic_allowlist=frozenset(raw.get("topic_allowlist") or []),
        topic_blocklist=frozenset(raw.get("topic_blocklist") or []),
        max_answers_per_day=int(raw.get("max_answers_per_day", 50)),
        min_payment=float(raw.get("min_payment", 0.0)),
        auto_submit_window_seconds=int(raw.get("auto_submit_window_seconds", 0)),
        auto_answer=bool(raw.get("auto_answer", False)),
    )


def decide(
    question: Question,
    policy: UserPolicy,
    stats: LedgerStats,
) -> Decision:
    """Pure decision function (§7.2).

    Note: deliberately does NOT inspect `question.text` for honeypot markers
    (§1.7). The only question property consulted is topic; asker identity is
    not part of the v0 broker protocol.
    """

    if not stats.has_active_delegation:
        return Decision(action="decline", reason="no active delegation token")

    if question.question_id in stats.already_answered_ids:
        # §1.9 idempotent. Don't re-answer.
        return Decision(action="decline", reason="already answered")

    if stats.answered_today >= policy.max_answers_per_day:
        return Decision(action="decline", reason="daily cap reached")

    topic = (question.topic or "").lower().strip()
    if topic and topic in policy.topic_blocklist:
        return Decision(action="decline", reason=f"topic blocked: {topic}")
    if policy.topic_allowlist and topic not in policy.topic_allowlist:
        return Decision(action="decline", reason=f"topic not in allowlist: {topic or '<none>'}")

    if not policy.auto_answer:
        return Decision(action="prompt_user", reason="auto-answer disabled (default)")

    return Decision(action="answer", reason="policy match")
