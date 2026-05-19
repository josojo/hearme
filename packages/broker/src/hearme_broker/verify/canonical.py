"""Deterministic canonical JSON for hashing.

ARCHITECTURE.md §8.5:
    delegation_hash = SHA-256(canonical_json(delegation_token))

Properties required:
- Keys sorted lexicographically at every nesting level (objects only).
- No insignificant whitespace (``separators=(",", ":")``).
- UTF-8 bytes out.
- Stable across input dict ordering.

We deliberately do not use a third-party JCS library to keep the surface
small and dependency-light. The rules below match the subset of RFC 8785
we actually need (objects, arrays, strings, numbers, bools, null).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID


def _normalize(value: Any) -> Any:
    """Coerce non-JSON-native types we use into stable JSON forms."""
    if isinstance(value, dict):
        # Sort keys; recursively normalize values.
        return {k: _normalize(value[k]) for k in sorted(value.keys())}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, datetime):
        # ISO-8601 with explicit Z for UTC — what we serialize on the wire.
        if value.tzinfo is None:
            return value.isoformat() + "Z"
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, UUID):
        return str(value)
    return value


def canonical_json(obj: Any) -> bytes:
    """Serialize ``obj`` to canonical-JSON bytes.

    Pure function. Two semantically equal inputs MUST produce identical bytes.
    """
    return json.dumps(
        _normalize(obj),
        separators=(",", ":"),
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")


def delegation_hash(token: dict[str, Any]) -> str:
    """SHA-256 of the canonical-JSON encoded DelegationToken, hex."""
    return hashlib.sha256(canonical_json(token)).hexdigest()
