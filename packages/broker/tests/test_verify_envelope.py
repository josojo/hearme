"""Envelope agent-signature verification.

Every swap of a signed field (question_id, answer, nonce, delegation_hash)
must reject — that's the linkage guarantee from ARCHITECTURE.md §1.9, §8.5.
"""

from __future__ import annotations

import base64
import uuid

import pytest

from hearme_broker.models.schemas import RejectionReason
from hearme_broker.verify.canonical import delegation_hash
from hearme_broker.verify.envelope import (
    VerifyEnvelopeError,
    verify_agent_signature,
)


def _verify(envelope: dict) -> None:
    dhash = delegation_hash(envelope["delegation_token"])
    verify_agent_signature(
        agent_pubkey_base64=envelope["delegation_token"]["agent_key"],
        question_id=envelope["question_id"],
        answer=envelope["answer"],
        nonce=envelope["nonce"],
        delegation_hash_hex=dhash,
        agent_signature_base64=envelope["agent_signature"],
    )


def test_happy_path(make_token, make_envelope):
    token = make_token()
    qid = uuid.uuid4()
    env = make_envelope(token, question_id=qid, answer="yes", nonce="nonce-abc")
    _verify(env)  # should not raise


def test_swap_question_id_rejected(make_token, make_envelope):
    token = make_token()
    env = make_envelope(
        token, question_id=uuid.uuid4(), answer="yes", nonce="nonce-abc"
    )
    env["question_id"] = str(uuid.uuid4())
    with pytest.raises(VerifyEnvelopeError) as exc:
        _verify(env)
    assert exc.value.reason is RejectionReason.AGENT_SIGNATURE_INVALID


def test_swap_answer_rejected(make_token, make_envelope):
    token = make_token()
    env = make_envelope(
        token, question_id=uuid.uuid4(), answer="yes", nonce="nonce-abc"
    )
    env["answer"] = "no"
    with pytest.raises(VerifyEnvelopeError) as exc:
        _verify(env)
    assert exc.value.reason is RejectionReason.AGENT_SIGNATURE_INVALID


def test_swap_nonce_rejected(make_token, make_envelope):
    token = make_token()
    env = make_envelope(
        token, question_id=uuid.uuid4(), answer="yes", nonce="nonce-abc"
    )
    env["nonce"] = "different-nonce"
    with pytest.raises(VerifyEnvelopeError) as exc:
        _verify(env)
    assert exc.value.reason is RejectionReason.AGENT_SIGNATURE_INVALID


def test_swap_delegation_hash_rejected(make_token, make_envelope):
    token = make_token()
    env = make_envelope(
        token, question_id=uuid.uuid4(), answer="yes", nonce="nonce-abc"
    )
    # Mutate the token so its recomputed delegation_hash differs from the
    # one the agent signed. (Phone signature would also break, but verifying
    # the agent step in isolation here: any tamper of the token bytes shifts
    # the hash and forces the agent signature to fail.)
    env["delegation_token"]["disclosed_predicates"] = {"region": "X"}
    with pytest.raises(VerifyEnvelopeError) as exc:
        _verify(env)
    assert exc.value.reason is RejectionReason.AGENT_SIGNATURE_INVALID


def test_malformed_agent_signature_rejected(make_token, make_envelope):
    token = make_token()
    env = make_envelope(
        token, question_id=uuid.uuid4(), answer="yes", nonce="nonce-abc"
    )
    env["agent_signature"] = base64.b64encode(b"\x00" * 64).decode("ascii")
    with pytest.raises(VerifyEnvelopeError) as exc:
        _verify(env)
    assert exc.value.reason is RejectionReason.AGENT_SIGNATURE_INVALID
