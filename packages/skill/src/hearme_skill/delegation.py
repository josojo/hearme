"""Delegation — § 7.5.

Loads the cached `DelegationToken` from encrypted-at-rest storage. v0 stubs
the encryption (see `crypto/keystore.py` for the same tradeoff). If the
token is expired or missing, this layer **fails the request** and raises an
exception that the UI layer can turn into a refresh nudge — it MUST NOT
silently call the phone (§1.13 phone is enrollment-only).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .crypto.canonical import delegation_hash as _delegation_hash
from .models import DelegationToken


class DelegationError(Exception):
    """Base class for delegation-layer failures."""


class DelegationMissing(DelegationError):
    """No delegation token on disk. User must run onboarding."""


class DelegationExpired(DelegationError):
    """Token expired. UI layer should prompt the user to refresh on the phone."""


# § 7.7 — nudge the user this far ahead of expiry.
REFRESH_WINDOW = timedelta(days=7)


# STUB: v0 stores the delegation token as plaintext JSON with 0600 perms.
# v0.1 should encrypt at rest. The same path/options apply as for the agent
# key (see crypto/keystore.py and ARCHITECTURE.md §13).
def store_delegation(path: Path, token: DelegationToken) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(token.model_dump(mode="json"), sort_keys=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload)
    tmp.chmod(0o600)
    tmp.replace(path)


def load_delegation(path: Path) -> DelegationToken:
    if not path.exists():
        raise DelegationMissing(f"No delegation token at {path}; run onboarding.")
    raw = json.loads(path.read_text())
    return DelegationToken.model_validate(raw)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def assert_usable(token: DelegationToken, *, now: datetime | None = None) -> None:
    """Raise DelegationExpired if the token cannot be used right now.

    Does NOT contact the phone. The skill never reaches outside the broker
    boundary in steady state.
    """

    current = now or _now()
    expires = token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= current:
        raise DelegationExpired(f"DelegationToken expired at {expires.isoformat()}")


def needs_refresh_soon(token: DelegationToken, *, now: datetime | None = None) -> bool:
    """True if we're inside the §7.7 7-day refresh window."""

    current = now or _now()
    expires = token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return (expires - current) <= REFRESH_WINDOW


def load_usable(path: Path, *, now: datetime | None = None) -> DelegationToken:
    """Load + check in one call. Raises on missing/expired."""

    tok = load_delegation(path)
    assert_usable(tok, now=now)
    return tok


def hash_of(token: DelegationToken) -> bytes:
    """SHA-256 of canonical_json(token). Matches the broker's verifier."""

    return _delegation_hash(token.model_dump(mode="json"))
