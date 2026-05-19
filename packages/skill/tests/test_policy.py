"""Policy tests — deterministic gate decisions (§7.2, §12).

The policy layer is a pure function; tests are unit-level and don't touch
the filesystem.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hearme_skill.policy import LedgerStats, UserPolicy, decide, load_policy


def test_decline_when_no_delegation(question):
    stats = LedgerStats(answered_today=0, has_active_delegation=False)
    d = decide(question, UserPolicy.default(), stats)
    assert d.action == "decline"
    assert "delegation" in d.reason


def test_decline_when_already_answered(question):
    stats = LedgerStats(already_answered_ids=frozenset({question.question_id}))
    d = decide(question, UserPolicy(auto_answer=True), stats)
    assert d.action == "decline"
    assert "already" in d.reason


def test_decline_when_topic_blocked(question):
    p = UserPolicy(topic_blocklist=frozenset({"coffee"}), auto_answer=True)
    d = decide(question, p, LedgerStats())
    assert d.action == "decline"


def test_decline_when_topic_not_in_allowlist(question):
    p = UserPolicy(topic_allowlist=frozenset({"travel"}), auto_answer=True)
    d = decide(question, p, LedgerStats())
    assert d.action == "decline"


def test_decline_when_daily_cap(question):
    p = UserPolicy(max_answers_per_day=3, auto_answer=True)
    d = decide(question, p, LedgerStats(answered_today=3))
    assert d.action == "decline"


def test_default_policy_is_prompt_user(question):
    # § 1.1: defaults to off; opt-in per category. Even a matching policy
    # must prompt the user unless `auto_answer` is explicitly true.
    p = UserPolicy(topic_allowlist=frozenset({"coffee"}))
    d = decide(question, p, LedgerStats())
    assert d.action == "prompt_user"


def test_answer_when_policy_matches_and_auto_answer_on(question):
    p = UserPolicy(topic_allowlist=frozenset({"coffee"}), auto_answer=True)
    d = decide(question, p, LedgerStats())
    assert d.action == "answer"


def test_policy_does_not_branch_on_question_text(question):
    """§1.7: policy MUST NOT inspect question text for honeypot markers."""

    # Inject obvious honeypot strings; decision must be unchanged.
    p = UserPolicy(topic_allowlist=frozenset({"coffee"}), auto_answer=True)
    baseline = decide(question, p, LedgerStats())
    for marker in ("HONEYPOT", "[TEST]", "is this a test?"):
        spiked = question.model_copy(update={"text": question.text + " " + marker})
        d = decide(spiked, p, LedgerStats())
        assert d.action == baseline.action, f"policy branched on text containing {marker!r}"


def test_load_policy_missing_file_returns_default(tmp_path: Path):
    p = load_policy(tmp_path / "missing.yaml")
    assert p == UserPolicy.default()


def test_load_policy_yaml(tmp_path: Path):
    path = tmp_path / "policy.yaml"
    path.write_text(
        "topic_allowlist:\n  - coffee\n"
        "max_answers_per_day: 5\n"
        "auto_answer: true\n"
        "auto_submit_window_seconds: 10\n"
    )
    p = load_policy(path)
    assert "coffee" in p.topic_allowlist
    assert p.max_answers_per_day == 5
    assert p.auto_answer is True
    assert p.auto_submit_window_seconds == 10


@pytest.mark.parametrize("answered,expected", [(0, "answer"), (49, "answer"), (50, "decline")])
def test_daily_cap_boundary(question, answered, expected):
    p = UserPolicy(topic_allowlist=frozenset({"coffee"}), auto_answer=True, max_answers_per_day=50)
    d = decide(question, p, LedgerStats(answered_today=answered))
    assert d.action == expected
