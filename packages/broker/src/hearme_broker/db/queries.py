"""All SQL the broker runs. Parameterized; no f-string SQL anywhere.

Group by responsibility so the audit boundary is obvious:
- ``questions_*`` — read-only against ``questions`` (per role grants).
- ``revocations_*`` — read-only against ``revocations`` for verify-time checks.
- ``envelopes_*`` — INSERT path only.
- ``aggregates_*`` — recompute on each insert.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg


# ----- questions ---------------------------------------------------------


async def list_open_questions(
    conn: asyncpg.Connection,
    *,
    since: datetime | None,
) -> list[dict[str, Any]]:
    """Open + not-yet-closed questions, optionally filtered by created_at >= since."""
    if since is None:
        rows = await conn.fetch(
            """
            SELECT id, text, topic, created_at, closes_at, nonce
            FROM questions
            WHERE status = 'open' AND closes_at > now()
            ORDER BY created_at ASC
            """
        )
    else:
        rows = await conn.fetch(
            """
            SELECT id, text, topic, created_at, closes_at, nonce
            FROM questions
            WHERE status = 'open' AND closes_at > now() AND created_at >= $1
            ORDER BY created_at ASC
            """,
            since,
        )
    return [dict(r) for r in rows]


async def get_question_for_verify(
    conn: asyncpg.Connection, question_id: UUID
) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        """
        SELECT id, status, closes_at, nonce
        FROM questions
        WHERE id = $1
        """,
        question_id,
    )
    return dict(row) if row else None


# ----- revocations -------------------------------------------------------


async def is_revoked(conn: asyncpg.Connection, delegation_hash_hex: str) -> bool:
    row = await conn.fetchrow(
        "SELECT 1 FROM revocations WHERE delegation_hash = $1",
        delegation_hash_hex,
    )
    return row is not None


# ----- envelopes ---------------------------------------------------------


async def insert_envelope(
    conn: asyncpg.Connection,
    *,
    question_id: UUID,
    unique_identifier: str,
    answer: str,
    disclosed_predicates: dict[str, str],
    agent_signature: str,
    delegation_hash_hex: str,
) -> bool:
    """INSERT one envelope; return False if PK collision (duplicate).

    The composite PK ``(question_id, unique_identifier)`` is the hard
    Sybil-resistance gate. We do an explicit ON CONFLICT DO NOTHING and
    return False so the caller can map to RejectionReason.DUPLICATE.
    """
    result = await conn.execute(
        """
        INSERT INTO envelopes (
          question_id, unique_identifier, answer, disclosed_predicates,
          agent_signature, delegation_hash
        ) VALUES ($1, $2, $3, $4::jsonb, $5, $6)
        ON CONFLICT (question_id, unique_identifier) DO NOTHING
        """,
        question_id,
        unique_identifier,
        answer,
        json.dumps(disclosed_predicates),
        agent_signature,
        delegation_hash_hex,
    )
    # asyncpg returns 'INSERT 0 1' on success, 'INSERT 0 0' on conflict.
    return result.endswith(" 1")


async def list_envelopes_for_question(
    conn: asyncpg.Connection, question_id: UUID
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT question_id, unique_identifier, disclosed_predicates
        FROM envelopes
        WHERE question_id = $1
        """,
        question_id,
    )
    out = []
    for r in rows:
        rec = dict(r)
        # asyncpg returns JSONB as already-decoded dict via codec config; but in
        # default config it returns a str. Normalize.
        if isinstance(rec.get("disclosed_predicates"), str):
            rec["disclosed_predicates"] = json.loads(rec["disclosed_predicates"])
        out.append(rec)
    return out


# ----- aggregates --------------------------------------------------------


async def upsert_aggregate(
    conn: asyncpg.Connection,
    *,
    question_id: UUID,
    total_answers: int,
    by_predicate: dict[str, int],
) -> None:
    await conn.execute(
        """
        INSERT INTO aggregates (question_id, total_answers, by_predicate, updated_at)
        VALUES ($1, $2, $3::jsonb, now())
        ON CONFLICT (question_id) DO UPDATE
        SET total_answers = EXCLUDED.total_answers,
            by_predicate  = EXCLUDED.by_predicate,
            updated_at    = now()
        """,
        question_id,
        total_answers,
        json.dumps(by_predicate),
    )
