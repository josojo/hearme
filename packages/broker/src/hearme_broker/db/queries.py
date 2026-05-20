"""All SQL the broker runs. Parameterized; no f-string SQL anywhere.

Group by responsibility so the audit boundary is obvious:
- ``questions_*`` — read-only against ``questions`` (per role grants).
- ``revocations_*`` — read-only against ``revocations`` for verify-time checks.
- ``envelopes_*`` — INSERT path only.
- ``aggregates_*`` — incremental update on each accepted insert.
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
        SELECT id, status, closes_at, nonce, scope, country, continent
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


# ----- registrations (nullifier registry) --------------------------------


async def upsert_registration(
    conn: asyncpg.Connection,
    *,
    unique_identifier: str,
    agent_key: str,
    disclosed_predicates: dict[str, str],
    issued_at: datetime,
    expires_at: datetime,
) -> str | None:
    """Atomically bind ``unique_identifier`` (nullifier) to ``agent_key``.

    Returns:
      - ``"created"``   — first registration of this nullifier.
      - ``"refreshed"`` — re-registration with the SAME agent_key (or after a
                          prior revocation): predicates/expiry updated.
      - ``None``        — the nullifier is already bound to a DIFFERENT,
                          non-revoked agent_key (the Sybil bind; reject).

    The single INSERT/ON CONFLICT statement holds the PK index lock, so two
    concurrent first registrations for one nullifier under different agent
    keys cannot both succeed.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO registrations (
          unique_identifier, agent_key, disclosed_predicates,
          issued_at, expires_at, revoked_at
        ) VALUES ($1, $2, $3::jsonb, $4, $5, NULL)
        ON CONFLICT (unique_identifier) DO UPDATE
        SET agent_key = EXCLUDED.agent_key,
            disclosed_predicates = EXCLUDED.disclosed_predicates,
            issued_at = EXCLUDED.issued_at,
            expires_at = EXCLUDED.expires_at,
            revoked_at = NULL
        WHERE registrations.agent_key = EXCLUDED.agent_key
           OR registrations.revoked_at IS NOT NULL
        RETURNING (xmax = 0) AS inserted
        """,
        unique_identifier,
        agent_key,
        json.dumps(disclosed_predicates),
        issued_at,
        expires_at,
    )
    if row is None:
        return None
    return "created" if row["inserted"] else "refreshed"


async def get_registration(
    conn: asyncpg.Connection, unique_identifier: str
) -> dict[str, Any] | None:
    """Return the registry row for ``unique_identifier`` (None if absent)."""
    row = await conn.fetchrow(
        """
        SELECT unique_identifier, agent_key, disclosed_predicates,
               issued_at, expires_at, revoked_at
        FROM registrations
        WHERE unique_identifier = $1
        """,
        unique_identifier,
    )
    return dict(row) if row else None


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


# ----- aggregates --------------------------------------------------------


async def increment_aggregate(
    conn: asyncpg.Connection,
    *,
    question_id: UUID,
    disclosed_predicates: dict[str, str],
) -> None:
    """Increment the aggregate row for one newly accepted envelope.

    The advisory transaction lock serializes first-writer creation of the
    aggregate row for a question. After that, ``FOR UPDATE`` locks only the
    single aggregate row, avoiding the previous full-envelope scan on every
    insert.
    """
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
        str(question_id),
    )
    row = await conn.fetchrow(
        """
        SELECT total_answers, by_predicate
        FROM aggregates
        WHERE question_id = $1
        FOR UPDATE
        """,
        question_id,
    )
    delta: dict[str, int] = {}
    for key, value in (disclosed_predicates or {}).items():
        predicate_key = f"{key}:{value}"
        delta[predicate_key] = delta.get(predicate_key, 0) + 1

    if row is None:
        await conn.execute(
            """
            INSERT INTO aggregates (question_id, total_answers, by_predicate, updated_at)
            VALUES ($1, 1, $2::jsonb, now())
            """,
            question_id,
            json.dumps(delta),
        )
        return

    by_predicate = row["by_predicate"]
    if isinstance(by_predicate, str):
        by_predicate = json.loads(by_predicate)
    by_predicate = dict(by_predicate or {})
    for key, count in delta.items():
        by_predicate[key] = int(by_predicate.get(key, 0)) + count

    await conn.execute(
        """
        UPDATE aggregates
        SET total_answers = total_answers + 1,
            by_predicate = $2::jsonb,
            updated_at = now()
        WHERE question_id = $1
        """,
        question_id,
        json.dumps(by_predicate),
    )
