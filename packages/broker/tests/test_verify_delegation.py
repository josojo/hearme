"""Delegation verification — happy path, expiry, bad sig.

Revocation is a DB lookup, tested in test_uniqueness.py against real Postgres.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest

from hearme_broker.models.schemas import DelegationToken, RejectionReason
from hearme_broker.verify.delegation import (
    VerifyDelegationError,
    verify_delegation,
)


def test_happy_path(make_token):
    raw = make_token()
    token = DelegationToken.model_validate(raw)
    out = verify_delegation(token)
    assert out.delegation_hash == out.delegation_hash  # sanity
    assert len(out.delegation_hash) == 64


def test_expired_token_rejected(make_token):
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    raw = make_token(
        issued_at=datetime.now(timezone.utc) - timedelta(days=100),
        expires_at=past,
    )
    token = DelegationToken.model_validate(raw)
    with pytest.raises(VerifyDelegationError) as exc:
        verify_delegation(token)
    assert exc.value.reason is RejectionReason.TOKEN_EXPIRED


def test_bad_phone_signature_rejected(make_token):
    raw = make_token()
    # Flip a byte in the signature.
    sig = bytearray(base64.b64decode(raw["phone_signature"]))
    sig[0] ^= 0xFF
    raw["phone_signature"] = base64.b64encode(bytes(sig)).decode("ascii")
    token = DelegationToken.model_validate(raw)
    with pytest.raises(VerifyDelegationError) as exc:
        verify_delegation(token)
    assert exc.value.reason is RejectionReason.PHONE_SIGNATURE_INVALID


def test_phone_signature_malformed_base64_rejected(make_token):
    raw = make_token()
    raw["phone_signature"] = "!!!not-base64!!!"
    token = DelegationToken.model_validate(raw)
    with pytest.raises(VerifyDelegationError) as exc:
        verify_delegation(token)
    assert exc.value.reason is RejectionReason.PHONE_SIGNATURE_INVALID


def test_mutating_token_breaks_phone_signature(make_token):
    raw = make_token()
    # Tamper with disclosed_predicates AFTER the phone signed.
    raw["disclosed_predicates"] = {"region": "non-EU", "age_band": "25-34"}
    token = DelegationToken.model_validate(raw)
    with pytest.raises(VerifyDelegationError) as exc:
        verify_delegation(token)
    assert exc.value.reason is RejectionReason.PHONE_SIGNATURE_INVALID
