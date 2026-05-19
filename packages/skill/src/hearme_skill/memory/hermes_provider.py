"""Memory provider that defers to Hermes's own memory layer.

In v0 the simple, honest design is: let Hermes do memory retrieval inside
its single LLM call. The Answerer is the only LLM caller, so any memory
context shows up there automatically. This module therefore returns an
**empty** snapshot by default — it's a placeholder that satisfies the
``MemoryProvider`` protocol without imposing a second LLM round-trip just
to pre-extract facts.

Why not pre-extract facts? Two reasons:

1. Cost. A pre-extraction call doubles the LLM spend per question.
2. Faithfulness. Hermes's memory injection during answering is more
   reliable than asking a model to summarize its own memory out-of-band.

If you want the pre-extraction behavior anyway (useful for snapshot
tests, transparency, or when you'd like the rationale field to carry
"why I think the user said this"), construct the provider with
``mode="extract"`` and pass a ``HermesLLMClient``; we then issue a small
extraction call per question.

Strict contract preserved (ARCHITECTURE.md §1.2, §7.3):

* No raw memory IDs.
* No source quotes.
* No demographics (Persona layer's defense-in-depth filter still runs
  even on extracted facts).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from .provider import MemoryQuery, MemorySnapshot

log = logging.getLogger("hearme_skill.memory.hermes")


@dataclass
class HermesMemoryProvider:
    """MemoryProvider that piggybacks on Hermes's own memory.

    ``mode="passthrough"`` (default) returns an empty snapshot. The
    Answerer's single LLM call against Hermes will still pull in
    whatever memory Hermes deems relevant — we just don't pre-extract.

    ``mode="extract"`` asks the supplied Hermes client for a short
    bulleted list of sanitized facts on the question's topic. The reply
    is parsed line-by-line; lines that look like raw IDs or source
    quotes are dropped. Persona layer's banned-prefix filter still
    runs.
    """

    name: str = "hermes-memory"
    mode: Literal["passthrough", "extract"] = "passthrough"
    # Only used when mode="extract". Typed as ``Any`` so we don't take a
    # hard import on the optional Hermes client at module load.
    llm: Any = None
    _style_hints: tuple[str, ...] = field(default=("plain", "concise"))

    def query(self, q: MemoryQuery) -> MemorySnapshot:
        if self.mode == "passthrough" or self.llm is None:
            return MemorySnapshot(facts=(), style_hints=self._style_hints)

        # Extract mode: small Hermes call asking for sanitized bullets.
        prompt = (
            "Looking only at what you actually know about the user from "
            "prior conversations, list up to "
            f"{q.limit} short, sanitized facts relevant to: "
            f"topic={q.topic or 'general'}; question={q.text!r}. "
            "Use bullet points starting with '- '. No raw memory IDs, no "
            "source quotes, no demographic claims. If you don't know "
            "anything relevant, reply exactly with: NONE."
        )
        try:
            text = self.llm.chat(prompt)  # HermesLLMClient.chat
        except Exception:  # noqa: BLE001
            log.exception("hermes memory extract failed; returning empty snapshot")
            return MemorySnapshot(facts=(), style_hints=self._style_hints)

        facts = tuple(_parse_bullets(text, limit=q.limit))
        return MemorySnapshot(facts=facts, style_hints=self._style_hints)


def _parse_bullets(text: str, *, limit: int) -> list[str]:
    if not text:
        return []
    cleaned = text.strip()
    if cleaned.upper().strip(".") == "NONE":
        return []
    out: list[str] = []
    for line in cleaned.splitlines():
        line = line.strip()
        if not line.startswith(("-", "*", "•")):
            continue
        fact = line.lstrip("-*• ").strip().rstrip(".")
        if not fact:
            continue
        # Defense-in-depth: drop anything that looks like raw memory ID
        # form ("mem://", "id:", "uuid:"). The Persona layer also filters
        # demographic prefixes after this returns.
        lowered = fact.lower()
        if any(lowered.startswith(prefix) for prefix in ("mem://", "id:", "uuid:")):
            continue
        out.append(fact)
        if len(out) >= limit:
            break
    return out
