"""Crypto helpers.

The broker's verifier must produce the exact same canonical-JSON bytes,
the same SHA-256 over them, and the same Ed25519 signature envelope. Keep
these helpers free of side-effects.
"""

from .canonical import canonical_json, canonical_json_bytes, delegation_hash, sign_payload
from .ed25519 import generate_keypair, sign, verify
from .keystore import load_agent_keypair, store_agent_keypair

__all__ = [
    "canonical_json",
    "canonical_json_bytes",
    "delegation_hash",
    "sign_payload",
    "generate_keypair",
    "sign",
    "verify",
    "load_agent_keypair",
    "store_agent_keypair",
]
