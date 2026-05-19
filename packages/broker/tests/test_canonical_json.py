"""canonical_json must be deterministic across key orderings."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from hearme_broker.verify.canonical import canonical_json, delegation_hash


def test_canonical_json_stable_across_orderings():
    a = {"b": 1, "a": 2, "c": {"y": 1, "x": 2}}
    b = {"c": {"x": 2, "y": 1}, "a": 2, "b": 1}
    assert canonical_json(a) == canonical_json(b)


def test_canonical_json_no_whitespace():
    out = canonical_json({"k": "v", "n": 1})
    assert out == b'{"k":"v","n":1}'


def test_canonical_json_datetime_roundtrips_to_z():
    dt = datetime(2026, 5, 19, 10, 0, 0, tzinfo=timezone.utc)
    out = json.loads(canonical_json({"t": dt}))
    assert out["t"].endswith("Z")


def test_delegation_hash_is_hex_64():
    h = delegation_hash({"version": 1, "domain": "hearme.network"})
    assert len(h) == 64
    int(h, 16)  # parses as hex


def test_delegation_hash_changes_on_mutation():
    base = {"version": 1, "domain": "hearme.network", "scope": "v1"}
    h1 = delegation_hash(base)
    h2 = delegation_hash({**base, "scope": "v2"})
    assert h1 != h2
