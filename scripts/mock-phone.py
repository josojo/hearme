#!/usr/bin/env python3
"""Mock phone — issues a DelegationToken signed with the dev phone key.

Per ARCHITECTURE.md §9 + §8.5. Used by the skill container's auto-onboarding
flow and by hand for local testing.

The dev phone keypair is deterministic so the broker can hardcode the matching
public key in `verify/well_known.py`. Real production has the phone hold the
private key and the broker resolve the public key via a trusted directory.

Usage:
    mock-phone.py mint --agent-pubkey-b64 <b64> [--unique-id <str>]
                       [--profile minimal|standard|granular]
                       [--ttl-days N]   > delegation.json

    mock-phone.py pubkey            # prints the dev phone public key (base64)
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from nacl.signing import SigningKey
except ImportError:
    sys.stderr.write(
        "mock-phone.py needs pynacl. Install it with: pip install pynacl\n"
    )
    raise


# Deterministic dev phone seed. The broker's well_known.py hardcodes the
# matching public key, so signatures verify out of the box.
DEV_PHONE_SEED = bytes([1] * 32)

# § 8.3 disclosure profiles. Real values would be derived from passport claims;
# here they're plausible defaults for the dev environment.
PROFILES: dict[str, dict[str, str]] = {
    "minimal": {"age_band": "18+", "region": "EU"},
    "standard": {"age_band": "25-34", "region": "EU", "gender": "n/a"},
    "granular": {
        "age_band": "25-34",
        "country": "DEU",
        "gender": "n/a",
        "urban_rural": "urban",
    },
}


# ---- canonical JSON (mirror of packages/broker/verify/canonical.py) -------


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize(value[k]) for k in sorted(value.keys())}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.isoformat() + "Z"
        return value.isoformat().replace("+00:00", "Z")
    return value


def canonical_json(obj: Any) -> bytes:
    return json.dumps(
        _normalize(obj),
        separators=(",", ":"),
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")


# ---- token construction ---------------------------------------------------


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def mint_token(
    *,
    agent_pubkey_b64: str,
    unique_id_seed: str,
    profile: str,
    ttl_days: int,
) -> dict:
    if profile not in PROFILES:
        raise SystemExit(f"unknown profile {profile!r}; choose from {list(PROFILES)}")

    # Validate agent pubkey is 32 bytes (Ed25519).
    try:
        raw_pub = base64.b64decode(agent_pubkey_b64)
    except Exception as exc:
        raise SystemExit(f"--agent-pubkey-b64 is not valid base64: {exc}")
    if len(raw_pub) != 32:
        raise SystemExit(f"--agent-pubkey-b64 decodes to {len(raw_pub)} bytes; want 32")

    # unique_identifier = scoped hash of (passport-secret, domain, scope).
    # Dev surrogate: hash(unique_id_seed || domain || scope).
    digest = hashlib.sha256(
        (unique_id_seed + "|hearme.network|v1").encode("utf-8")
    ).digest()
    unique_identifier = base64.b64encode(digest).decode("ascii")

    now = datetime.now(timezone.utc)
    token: dict = {
        "version": 1,
        "zkpassport_proof": base64.b64encode(b"stub-zkpassport-proof").decode("ascii"),
        "domain": "hearme.network",
        "scope": "v1",
        "unique_identifier": unique_identifier,
        "disclosed_predicates": PROFILES[profile],
        "agent_key": agent_pubkey_b64,
        "issued_at": _iso_z(now),
        "expires_at": _iso_z(now + timedelta(days=ttl_days)),
    }

    signing_key = SigningKey(DEV_PHONE_SEED)
    signature = signing_key.sign(canonical_json(token)).signature
    token["phone_signature"] = base64.b64encode(signature).decode("ascii")
    return token


# ---- CLI ------------------------------------------------------------------


def _cmd_mint(args: argparse.Namespace) -> int:
    token = mint_token(
        agent_pubkey_b64=args.agent_pubkey_b64,
        unique_id_seed=args.unique_id,
        profile=args.profile,
        ttl_days=args.ttl_days,
    )
    json.dump(token, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _cmd_pubkey(_: argparse.Namespace) -> int:
    sk = SigningKey(DEV_PHONE_SEED)
    print(base64.b64encode(bytes(sk.verify_key)).decode("ascii"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mock-phone.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_mint = sub.add_parser("mint", help="Mint a signed DelegationToken")
    p_mint.add_argument("--agent-pubkey-b64", required=True)
    p_mint.add_argument(
        "--unique-id",
        default="dev-user-1",
        help="Surrogate for the passport secret; same seed → same unique_identifier.",
    )
    p_mint.add_argument("--profile", default="standard", choices=list(PROFILES))
    p_mint.add_argument("--ttl-days", type=int, default=90)
    p_mint.set_defaults(func=_cmd_mint)

    p_pub = sub.add_parser("pubkey", help="Print the dev phone public key")
    p_pub.set_defaults(func=_cmd_pubkey)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
