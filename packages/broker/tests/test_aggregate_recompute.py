"""Aggregate helpers — by_predicate must match hand computation.

Pure-function test for ``compute_by_predicate`` plus an end-to-end run
against real Postgres for incremental aggregate updates.
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from hearme_broker.aggregates import classify_vote, compute_by_predicate
from hearme_broker.db import queries as q


def test_classify_vote_reads_leading_word_across_languages():
    assert classify_vote("Yes — auditability beats virality.") == "yes"
    assert classify_vote("no way, that's worse") == "no"
    assert classify_vote("Sim, mudou tudo.") == "yes"
    assert classify_vote("Nein, das hilft nicht.") == "no"
    assert classify_vote("Oui, c'est viable.") == "yes"
    assert classify_vote("Sí, claramente.") == "yes"
    # Unclassifiable / empty -> None (still counts toward total_answers).
    assert classify_vote("Both at once, honestly.") is None
    assert classify_vote("") is None
    assert classify_vote(None) is None


def test_compute_by_predicate_hand_computation():
    envelopes = [
        {"answer": "Yes, definitely.", "disclosed_predicates": {"region": "EU", "age_band": "25-34"}},
        {"answer": "No way.", "disclosed_predicates": {"region": "EU", "age_band": "35-44"}},
        {"answer": "yes", "disclosed_predicates": {"region": "non-EU", "age_band": "25-34"}},
        {"answer": "Yes — strongly.", "disclosed_predicates": {"region": "EU", "age_band": "25-34"}},
    ]
    assert compute_by_predicate(envelopes) == {
        "region:EU": {"yes": 2, "no": 1},
        "region:non-EU": {"yes": 1, "no": 0},
        "age_band:25-34": {"yes": 3, "no": 0},
        "age_band:35-44": {"yes": 0, "no": 1},
    }


def test_compute_by_predicate_empty():
    assert compute_by_predicate([]) == {}


def test_compute_by_predicate_handles_missing_field():
    envelopes = [
        {"answer": "yes", "disclosed_predicates": None},
        {"answer": "no", "disclosed_predicates": {}},
        {"answer": "Yes", "disclosed_predicates": {"region": "EU"}},
    ]
    assert compute_by_predicate(envelopes) == {"region:EU": {"yes": 1, "no": 0}}


def test_compute_by_predicate_handles_json_string_from_asyncpg():
    envelopes = [
        {"answer": "No, not really.", "disclosed_predicates": '{"region":"EU","age_band":"25-34"}'},
    ]
    assert compute_by_predicate(envelopes) == {
        "region:EU": {"yes": 0, "no": 1},
        "age_band:25-34": {"yes": 0, "no": 1},
    }


pytestmark_async = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_increment_aggregate_against_real_pg(pg_pool):
    # Seed 3 accepted envelopes for one yes/no question; assert the yes/no
    # tally per predicate matches.
    qid = uuid.uuid4()
    async with pg_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO questions (id, text, nonce, closes_at, status)
            VALUES ($1, $2, $3, $4, 'open')
            """,
            qid,
            "agg question",
            "agg-nonce",
            datetime.now(timezone.utc) + timedelta(hours=1),
        )

        # Three distinct users with mixed predicates and yes/no votes.
        users = [
            (base64.b64encode(b"\x10" * 32).decode("ascii"), "Yes, agree.", {"region": "EU", "age_band": "25-34"}),
            (base64.b64encode(b"\x11" * 32).decode("ascii"), "No, disagree.", {"region": "EU", "age_band": "35-44"}),
            (base64.b64encode(b"\x12" * 32).decode("ascii"), "yes", {"region": "non-EU", "age_band": "25-34"}),
        ]
        for uid, ans, preds in users:
            await q.insert_envelope(
                conn,
                question_id=qid,
                unique_identifier=uid,
                answer=ans,
                disclosed_predicates=preds,
                agent_signature="sig",
                delegation_hash_hex="hash",
            )
            await q.increment_aggregate(
                conn,
                question_id=qid,
                answer=ans,
                disclosed_predicates=preds,
            )

        row = await conn.fetchrow(
            "SELECT total_answers, by_predicate FROM aggregates WHERE question_id = $1",
            qid,
        )
        assert row["total_answers"] == 3
        import json as _json
        by_pred = row["by_predicate"]
        if isinstance(by_pred, str):
            by_pred = _json.loads(by_pred)
        assert by_pred == {
            "region:EU": {"yes": 1, "no": 1},
            "region:non-EU": {"yes": 1, "no": 0},
            "age_band:25-34": {"yes": 2, "no": 0},
            "age_band:35-44": {"yes": 0, "no": 1},
        }
