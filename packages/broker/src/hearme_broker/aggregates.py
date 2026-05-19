"""Recompute the ``aggregates`` row for a question.

Called inside the same transaction as the envelope INSERT so a reader can
never see total_answers drift from the envelope count.

The shape of ``by_predicate`` matches the schema comment and §3 of
ARCHITECTURE.md: ``{"region:EU": 42, "age_band:25-34": 17, ...}`` — one
counter per (predicate_name, predicate_value) pair across all envelopes
for the question.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg

from .db import queries as q


def compute_by_predicate(envelopes: list[dict[str, Any]]) -> dict[str, int]:
    """Pure function — easy to unit-test."""
    out: dict[str, int] = {}
    for env in envelopes:
        preds = env.get("disclosed_predicates") or {}
        for k, v in preds.items():
            key = f"{k}:{v}"
            out[key] = out.get(key, 0) + 1
    return out


async def recompute(conn: asyncpg.Connection, question_id: UUID) -> None:
    """Read all envelopes for the question, recompute, upsert."""
    envelopes = await q.list_envelopes_for_question(conn, question_id)
    by_pred = compute_by_predicate(envelopes)
    await q.upsert_aggregate(
        conn,
        question_id=question_id,
        total_answers=len(envelopes),
        by_predicate=by_pred,
    )
