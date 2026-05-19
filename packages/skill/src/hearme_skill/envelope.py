"""Envelope — § 7.5.

Builds the five-field POST body (ARCHITECTURE.md §8.5) and signs it with the
agent key. The signature covers
``H(question_id || answer || nonce || delegation_hash)`` so envelopes can't be
replayed against a different question (§1.9).
"""

from __future__ import annotations

import base64

from .crypto.canonical import sign_payload
from .crypto.ed25519 import Keypair, sign
from .delegation import hash_of
from .models import DelegationToken, Envelope


def build_envelope(
    *,
    question_id: str,
    answer_text: str,
    nonce: str,
    delegation_token: DelegationToken,
    agent_key: Keypair,
) -> Envelope:
    """Construct + sign an envelope.

    Note the function takes `answer_text: str`, not `Answer`. This is on
    purpose: the local-only `Answer.rationale` field must never leak into
    the envelope. Callers extract `.text` themselves.
    """

    dhash_hex = hash_of(delegation_token).hex()
    payload = sign_payload(question_id, answer_text, nonce, dhash_hex)
    sig = sign(agent_key, payload)
    return Envelope(
        question_id=question_id,
        answer=answer_text,
        nonce=nonce,
        delegation_token=delegation_token,
        agent_signature=base64.b64encode(sig).decode("ascii"),
    )


def serialize_envelope(env: Envelope) -> dict:
    """Dict ready for `httpx.post(..., json=...)`. Five fields, no extras."""

    body = env.model_dump(mode="json")
    # Defensive check — the boundary-leakage test in §12 verifies this from
    # the wire side, but we also sanity-check here.
    expected = {"question_id", "answer", "nonce", "delegation_token", "agent_signature"}
    if set(body.keys()) != expected:
        raise RuntimeError(
            f"Envelope serialization carries unexpected keys: {set(body.keys()) ^ expected}"
        )
    return body
