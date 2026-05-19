"""Ledger — § 7.6.

Local SQLite via aiosqlite. Schema: ``questions``, ``answers``, ``submissions``,
``revocations``, ``question_spend``. Primary key on `question_id` everywhere.

# STUB: v0 does not encrypt the ledger at rest. SQLCipher / OS keychain in
# v0.1 — see ARCHITECTURE.md §13 ("DelegationToken storage at rest" — same
# tradeoff). The rationale and other locally-sensitive material live here;
# host compromise == ledger leak in v0.

Read-only views to the UI layer are exposed via `LedgerReader`. The Channel
+ Envelope layers use the full `Ledger` to write.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS questions (
    question_id TEXT PRIMARY KEY,
    text        TEXT NOT NULL,
    topic       TEXT,
    closes_at   TEXT NOT NULL,
    nonce       TEXT NOT NULL,
    received_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS answers (
    question_id TEXT PRIMARY KEY REFERENCES questions(question_id),
    answer_text TEXT NOT NULL,
    rationale   TEXT NOT NULL,           -- local-only; never serialized
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    question_id     TEXT PRIMARY KEY REFERENCES questions(question_id),
    delegation_hash TEXT NOT NULL,
    agent_signature TEXT NOT NULL,
    submitted_at    TEXT NOT NULL,
    accepted        INTEGER NOT NULL DEFAULT 0,
    reason          TEXT
);

CREATE TABLE IF NOT EXISTS revocations (
    delegation_hash TEXT PRIMARY KEY,
    revoked_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS question_spend (
    day           TEXT PRIMARY KEY,        -- YYYY-MM-DD, UTC
    answer_count  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _today_utc() -> str:
    return datetime.now(tz=timezone.utc).date().isoformat()


@dataclass(frozen=True)
class SubmissionRecord:
    question_id: str
    delegation_hash: str
    agent_signature: str
    submitted_at: str
    accepted: bool
    reason: str | None


class LedgerReader(Protocol):
    """Read-only view exposed to the UI layer (§7.6 read-only views)."""

    async def list_recent_submissions(self, limit: int = 20) -> list[SubmissionRecord]: ...
    async def get_submission(self, question_id: str) -> SubmissionRecord | None: ...
    async def last_seen_cursor(self) -> str | None: ...


class Ledger:
    """Read/write ledger. Async; safe to share across the skill's tasks."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._db: aiosqlite.Connection | None = None

    async def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Ledger not opened. Call await ledger.open() first.")
        return self._db

    # --- writes -------------------------------------------------------

    async def record_question(
        self,
        question_id: str,
        text: str,
        topic: str | None,
        closes_at: datetime,
        nonce: str,
    ) -> None:
        await self._conn().execute(
            "INSERT OR IGNORE INTO questions(question_id, text, topic, closes_at, nonce, received_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (question_id, text, topic, closes_at.isoformat(), nonce, _now_iso()),
        )
        await self._conn().commit()

    async def record_answer(self, question_id: str, answer_text: str, rationale: str) -> None:
        await self._conn().execute(
            "INSERT OR REPLACE INTO answers(question_id, answer_text, rationale, created_at)"
            " VALUES (?, ?, ?, ?)",
            (question_id, answer_text, rationale, _now_iso()),
        )
        await self._conn().commit()

    async def record_submission(
        self,
        question_id: str,
        delegation_hash_hex: str,
        agent_signature_b64: str,
        accepted: bool,
        reason: str | None,
    ) -> None:
        await self._conn().execute(
            "INSERT OR REPLACE INTO submissions"
            " (question_id, delegation_hash, agent_signature, submitted_at, accepted, reason)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                question_id,
                delegation_hash_hex,
                agent_signature_b64,
                _now_iso(),
                1 if accepted else 0,
                reason,
            ),
        )
        if accepted:
            await self._conn().execute(
                "INSERT INTO question_spend(day, answer_count) VALUES (?, 1)"
                " ON CONFLICT(day) DO UPDATE SET answer_count = answer_count + 1",
                (_today_utc(),),
            )
        await self._conn().commit()

    async def set_last_seen(self, cursor: str) -> None:
        await self._conn().execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('last_seen', ?)",
            (cursor,),
        )
        await self._conn().commit()

    # --- reads --------------------------------------------------------

    async def has_submission(self, question_id: str) -> bool:
        async with self._conn().execute(
            "SELECT 1 FROM submissions WHERE question_id = ? AND accepted = 1",
            (question_id,),
        ) as cur:
            row = await cur.fetchone()
        return row is not None

    async def get_submission(self, question_id: str) -> SubmissionRecord | None:
        async with self._conn().execute(
            "SELECT question_id, delegation_hash, agent_signature, submitted_at, accepted, reason"
            " FROM submissions WHERE question_id = ?",
            (question_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return SubmissionRecord(
            question_id=row[0],
            delegation_hash=row[1],
            agent_signature=row[2],
            submitted_at=row[3],
            accepted=bool(row[4]),
            reason=row[5],
        )

    async def list_recent_submissions(self, limit: int = 20) -> list[SubmissionRecord]:
        async with self._conn().execute(
            "SELECT question_id, delegation_hash, agent_signature, submitted_at, accepted, reason"
            " FROM submissions ORDER BY submitted_at DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
        return [
            SubmissionRecord(
                question_id=r[0],
                delegation_hash=r[1],
                agent_signature=r[2],
                submitted_at=r[3],
                accepted=bool(r[4]),
                reason=r[5],
            )
            for r in rows
        ]

    async def last_seen_cursor(self) -> str | None:
        async with self._conn().execute(
            "SELECT value FROM meta WHERE key = 'last_seen'"
        ) as cur:
            row = await cur.fetchone()
        return row[0] if row else None

    async def answered_today(self) -> int:
        async with self._conn().execute(
            "SELECT answer_count FROM question_spend WHERE day = ?",
            (_today_utc(),),
        ) as cur:
            row = await cur.fetchone()
        return int(row[0]) if row else 0

    async def already_answered_ids(self) -> frozenset[str]:
        async with self._conn().execute(
            "SELECT question_id FROM submissions WHERE accepted = 1"
        ) as cur:
            rows = await cur.fetchall()
        return frozenset(r[0] for r in rows)
