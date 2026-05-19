"""Ed25519 sign/verify wrappers around PyNaCl.

Keep this layer dumb: it knows nothing about envelopes, delegation tokens,
or the rest of the protocol. Callers handle hashing/canonicalization.
"""

from __future__ import annotations

from dataclasses import dataclass

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey


@dataclass(frozen=True)
class Keypair:
    """Raw 32-byte seed + derived 32-byte public key."""

    signing_key: SigningKey
    verify_key: VerifyKey

    @property
    def public_bytes(self) -> bytes:
        return bytes(self.verify_key)

    @property
    def private_bytes(self) -> bytes:
        return bytes(self.signing_key)


def generate_keypair() -> Keypair:
    sk = SigningKey.generate()
    return Keypair(signing_key=sk, verify_key=sk.verify_key)


def keypair_from_seed(seed: bytes) -> Keypair:
    sk = SigningKey(seed)
    return Keypair(signing_key=sk, verify_key=sk.verify_key)


def sign(keypair: Keypair, payload: bytes) -> bytes:
    """Return raw 64-byte Ed25519 signature over `payload`."""

    return keypair.signing_key.sign(payload).signature


def verify(public_key: bytes, payload: bytes, signature: bytes) -> bool:
    try:
        VerifyKey(public_key).verify(payload, signature)
        return True
    except BadSignatureError:
        return False
