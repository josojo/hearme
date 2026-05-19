"""DB-level uniqueness — same (question_id, unique_identifier) twice → reject.

Runs against a real Postgres via ``testcontainers``. Skipped if Docker
is unavailable. Also exercises the revocations path end-to-end (the DB
lookup in routes/envelopes.py).
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from hearme_broker.db import queries as q
from hearme_broker.models.schemas import DelegationToken, Envelope, RejectionReason
from hearme_broker.verify.canonical import delegation_hash
from hearme_broker.verify.delegation import verify_delegation


pytestmark = pytest.mark.asyncio


async def _seed_question(pool, *, nonce: str, status: str = "open") -> uuid.UUID:
    qid = uuid.uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO questions (id, text, topic, nonce, closes_at, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            qid,
            "test question",
            "test",
            nonce,
            datetime.now(timezone.utc) + timedelta(hours=1),
            status,
        )
    return qid


async def test_duplicate_envelope_rejected_at_db(pg_pool, make_token, make_envelope):
    qid = await _seed_question(pg_pool, nonce="seed-nonce-1")
    token_dict = make_token()
    env_dict = make_envelope(
        token_dict, question_id=qid, answer="first", nonce="seed-nonce-1"
    )

    env = Envelope.model_validate(env_dict)
    verified = verify_delegation(env.delegation_token)

    async with pg_pool.acquire() as conn:
        ok1 = await q.insert_envelope(
            conn,
            question_id=env.question_id,
            unique_identifier=verified.token.unique_identifier,
            answer=env.answer,
            disclosed_predicates=verified.token.disclosed_predicates,
            agent_signature=env.agent_signature,
            delegation_hash_hex=verified.delegation_hash,
        )
        assert ok1 is True

        # Second insert with same unique_identifier for same question must fail.
        env2_dict = make_envelope(
            token_dict, question_id=qid, answer="second", nonce="seed-nonce-1"
        )
        env2 = Envelope.model_validate(env2_dict)
        ok2 = await q.insert_envelope(
            conn,
            question_id=env2.question_id,
            unique_identifier=verified.token.unique_identifier,
            answer=env2.answer,
            disclosed_predicates=verified.token.disclosed_predicates,
            agent_signature=env2.agent_signature,
            delegation_hash_hex=verified.delegation_hash,
        )
        assert ok2 is False


async def test_revocation_lookup(pg_pool, make_token):
    token_dict = make_token()
    dhash = delegation_hash(token_dict)
    async with pg_pool.acquire() as conn:
        assert await q.is_revoked(conn, dhash) is False
        await conn.execute(
            "INSERT INTO revocations (delegation_hash) VALUES ($1)", dhash
        )
        assert await q.is_revoked(conn, dhash) is True


async def test_different_uids_can_both_answer(pg_pool, make_token, make_envelope):
    qid = await _seed_question(pg_pool, nonce="seed-nonce-2")
    token_a = make_token(
        unique_identifier=base64.b64encode(b"\x0a" * 32).decode("ascii"),
        disclosed_predicates={"region": "EU"},
    )
    token_b = make_token(
        unique_identifier=base64.b64encode(b"\x0b" * 32).decode("ascii"),
        disclosed_predicates={"region": "non-EU"},
    )

    async with pg_pool.acquire() as conn:
        for t in (token_a, token_b):
            env_dict = make_envelope(t, question_id=qid, answer="x", nonce="seed-nonce-2")
            env = Envelope.model_validate(env_dict)
            verified = verify_delegation(env.delegation_token)
            ok = await q.insert_envelope(
                conn,
                question_id=env.question_id,
                unique_identifier=verified.token.unique_identifier,
                answer=env.answer,
                disclosed_predicates=verified.token.disclosed_predicates,
                agent_signature=env.agent_signature,
                delegation_hash_hex=verified.delegation_hash,
            )
            assert ok is True
