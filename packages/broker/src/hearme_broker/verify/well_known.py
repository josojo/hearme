"""Well-known phone pubkey used to verify DelegationToken.phone_signature.

v0: hardcoded. In v0.2+ this is fetched from a trusted directory (or
the ZKPassport service's public registry) — see ARCHITECTURE.md §11
("Real zkPassport proof verification" stub).

Environment overrides:
    HEARME_PHONE_PUBKEY_BASE64  — base64 Ed25519 pubkey (32 bytes)

That env hook exists so tests can substitute a key produced by their own
signer. The function reads at call time so test fixtures monkeypatching
``os.environ`` see the change.
"""

from __future__ import annotations

import base64
import os

from nacl.signing import VerifyKey

# STUB: v0 trusts a single phone pubkey. In production, the broker should
# resolve the right phone key for the user via the DelegationToken's
# attestation chain rooted in ZKPassport. Not yet real.
#
# This default matches the deterministic dev keypair in scripts/mock-phone.py
# (Ed25519 seed = bytes([1] * 32)) so `docker compose up` works without
# additional configuration. Tests override via HEARME_PHONE_PUBKEY_BASE64.
_DEV_PHONE_PUBKEY_BASE64 = "iojj3XQJ8ZX9UtstPLpdcspnCb8dlBIb83SIAbQPb1w="


def phone_pubkey_base64() -> str:
    return os.environ.get("HEARME_PHONE_PUBKEY_BASE64", _DEV_PHONE_PUBKEY_BASE64)


def phone_verify_key() -> VerifyKey:
    raw = base64.b64decode(phone_pubkey_base64())
    if len(raw) != 32:
        raise ValueError(
            f"phone pubkey must be 32 bytes (got {len(raw)}); check HEARME_PHONE_PUBKEY_BASE64"
        )
    return VerifyKey(raw)
