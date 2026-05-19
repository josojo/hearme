"""# STUB: v0 hardcoded memory provider.

Per ARCHITECTURE.md §11 ("Memory provider abstraction"), v0 ships exactly
one provider. We call it "Mem0" so the integration path is obvious, but it
is in fact a deterministic synthetic store: it returns short, sanitized
facts derived from a small per-topic table.

v0.2 swaps this for Hermes's real memory abstraction.
"""

from __future__ import annotations

from .provider import MemoryQuery, MemorySnapshot

# A tiny synthetic store so persona projection snapshot tests are stable.
# Topics map to short, sanitized facts. No PII, no source quotes, no
# memory IDs — the contract in `MemoryProvider`.
_SYNTHETIC_FACTS: dict[str, tuple[str, ...]] = {
    "coffee": (
        "prefers single-origin pourover in the morning",
        "drinks decaf after 3pm",
    ),
    "travel": (
        "has spent extended time in southern Europe",
        "prefers slow travel over packed itineraries",
    ),
    "work": (
        "writes software for a living",
        "values async-first collaboration",
    ),
}

_STYLE_BY_TOPIC: dict[str, tuple[str, ...]] = {
    "coffee": ("conversational", "specific about brewing methods"),
    "travel": ("storyteller", "favors concrete sensory detail"),
    "work": ("direct", "structured"),
}

_DEFAULT_FACTS: tuple[str, ...] = ("no strong opinions recorded for this topic",)
_DEFAULT_STYLE: tuple[str, ...] = ("plain", "concise")


class Mem0StubProvider:
    """Deterministic synthetic provider. v0 only."""

    name = "mem0-stub"

    def __init__(self, store: dict[str, tuple[str, ...]] | None = None) -> None:
        # Allow tests to inject an alternate table while still exercising the
        # determinism guarantee.
        self._store = store if store is not None else _SYNTHETIC_FACTS

    def query(self, q: MemoryQuery) -> MemorySnapshot:
        topic = (q.topic or "").lower().strip()
        facts = self._store.get(topic, _DEFAULT_FACTS)
        style = _STYLE_BY_TOPIC.get(topic, _DEFAULT_STYLE)
        return MemorySnapshot(facts=tuple(facts[: q.limit]), style_hints=style)
