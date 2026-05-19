"""Persona — § 7.3.

Pure projection from memory to a minimal sanitized snapshot. No raw memory
IDs, no source quotes, no demographic fields (demographics live in the
DelegationToken, never here).

Determinism: same `(question, memory_state)` → same projection. The
`Mem0StubProvider` is itself deterministic, so this function is too.
"""

from __future__ import annotations

from .memory.provider import MemoryProvider, MemoryQuery
from .models import PersonaProjection, Question


def project(question: Question, memory: MemoryProvider) -> PersonaProjection:
    snapshot = memory.query(
        MemoryQuery(topic=question.topic, text=question.text, limit=5)
    )

    # Defense-in-depth: enforce the no-demographics contract on the way out.
    # If any fact looks like a demographic claim, drop it.
    _BANNED_PREFIXES = ("age:", "gender:", "country:", "region:", "ethnicity:")
    filtered_facts = tuple(
        f for f in snapshot.facts
        if not any(f.lower().startswith(p) for p in _BANNED_PREFIXES)
    )

    return PersonaProjection(
        topic=question.topic,
        relevant_facts=list(filtered_facts),
        style_hints=list(snapshot.style_hints),
    )
