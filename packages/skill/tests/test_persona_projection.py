"""Persona projection — snapshot tests (§7.3, §12).

Asserts:
* Output is deterministic for the same (question, memory_state).
* NO demographic fields (`age:`, `gender:`, `country:`, `region:`, `ethnicity:`).
* NO raw memory IDs / source quotes (the Mem0 stub itself doesn't emit them;
  this test guards the persona layer's filtering belt).
"""

from __future__ import annotations

from hearme_skill.memory.mem0_stub import Mem0StubProvider
from hearme_skill.memory.provider import MemoryQuery, MemorySnapshot
from hearme_skill.persona import project


def test_projection_is_deterministic(question):
    provider = Mem0StubProvider()
    p1 = project(question, provider)
    p2 = project(question, provider)
    assert p1.model_dump() == p2.model_dump()


def test_projection_snapshot_coffee(question):
    """Snapshot test — coffee topic."""

    provider = Mem0StubProvider()
    p = project(question, provider)
    assert p.model_dump() == {
        "topic": "coffee",
        "relevant_facts": [
            "prefers single-origin pourover in the morning",
            "drinks decaf after 3pm",
        ],
        "style_hints": ["conversational", "specific about brewing methods"],
    }


def test_projection_filters_demographic_leaks(question):
    """If a misbehaving provider leaks demographics, persona drops them."""

    class LeakyProvider:
        def query(self, q: MemoryQuery) -> MemorySnapshot:  # noqa: D401
            return MemorySnapshot(
                facts=(
                    "Age: 31",
                    "Gender: female",
                    "Region: EU",
                    "drinks decaf after 3pm",
                ),
                style_hints=(),
            )

    p = project(question, LeakyProvider())
    for fact in p.relevant_facts:
        lower = fact.lower()
        assert not lower.startswith(("age:", "gender:", "country:", "region:", "ethnicity:"))
    assert "drinks decaf after 3pm" in p.relevant_facts


def test_projection_carries_no_raw_memory_ids(question):
    provider = Mem0StubProvider()
    p = project(question, provider)
    flat = repr(p.model_dump())
    # No UUIDs, no "memory:" prefixes, no source-quote markers.
    assert "memory:" not in flat
    assert "src=" not in flat
    # No 32-or-more-char hex blobs (a crude raw-ID heuristic).
    import re

    assert re.search(r"[0-9a-f]{32,}", flat) is None
