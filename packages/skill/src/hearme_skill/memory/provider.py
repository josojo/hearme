"""Memory provider abstraction (ARCHITECTURE.md §1.11, §11).

Hermes supports many memory backends; the skill never imports a specific one.
v0 ships one hardcoded stub (`Mem0StubProvider`). v0.2 wires this protocol to
Hermes's real memory abstraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MemoryQuery:
    """Question-scoped query into the user's memory.

    Topic is the only routing hint v0 uses. Limit caps the snapshot size so
    we never accidentally inflate the persona projection.
    """

    topic: str | None
    text: str
    limit: int = 5


@dataclass(frozen=True)
class MemorySnapshot:
    """Sanitized snapshot returned by the provider.

    `facts` are short, derived statements — never raw memory IDs, never
    source quotes. `style_hints` describe how the user tends to phrase
    answers on this topic.

    No demographic fields here. Demographics live in the DelegationToken.
    """

    facts: tuple[str, ...]
    style_hints: tuple[str, ...] = ()


class MemoryProvider(Protocol):
    """The handle Persona uses to consult memory.

    Implementations must:

    * Be deterministic for identical inputs (so persona projection snapshots
      stay stable in tests; see ARCHITECTURE.md §7.3).
    * Return ONLY sanitized facts — no raw memory IDs, no source quotes, no
      demographics.
    """

    def query(self, q: MemoryQuery) -> MemorySnapshot: ...
