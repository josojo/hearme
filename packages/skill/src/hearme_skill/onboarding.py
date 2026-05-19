"""Onboarding — § 8.

The one moment the phone produces cryptographic material for the agent.

Flow:
  1. Skill generates an Ed25519 keypair (`agent_key`).
  2. Skill displays a QR code containing: agent_key.public, hermes node id,
     a fresh onboarding nonce, and the disclosure profiles (§8.3).
  3. User scans QR in ZKPassport app, picks a disclosure profile.
  4. Phone produces a DelegationToken and sends it to the agent over the
     paired channel.
  5. Skill encrypts (STUB: v0 stores plaintext with 0600 perms) and stores
     at `~/.hermes/hearme/delegation.token`.

For development, `accept_delegation_from_mock_phone()` accepts a
DelegationToken JSON produced by `scripts/mock-phone.py` and stores it the
same way as the real flow.
"""

from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass
from pathlib import Path

from .crypto.keystore import load_or_create_agent_keypair
from .delegation import store_delegation
from .models import DelegationToken

# § 8.3 disclosure profiles. Fixed bundles, picked once on the phone.
DISCLOSURE_PROFILES = {
    "minimal": {
        "age_band": "18+ / under-18",
        "region": "EU / non-EU",
    },
    "standard": {
        "age_band": "5-year-bucket",
        "region": "continent",
        "gender": "optional",
    },
    "granular": {
        "age_band": "5-year-bucket",
        "country": "ISO-3166",
        "gender": "optional",
        "urban_rural": "optional",
    },
}


@dataclass(frozen=True)
class OnboardingHandoff:
    """Data the QR code conveys to the phone."""

    agent_public_key: str  # base64
    hermes_node_id: str
    onboarding_nonce: str  # base64
    disclosure_profiles: dict[str, dict[str, str]]

    def to_qr_payload(self) -> str:
        return json.dumps(
            {
                "agent_public_key": self.agent_public_key,
                "hermes_node_id": self.hermes_node_id,
                "onboarding_nonce": self.onboarding_nonce,
                "disclosure_profiles": self.disclosure_profiles,
            },
            sort_keys=True,
        )


def begin_onboarding(*, agent_key_path: Path, hermes_node_id: str) -> OnboardingHandoff:
    """Generate the agent key (if needed) and build the QR payload.

    Idempotent: re-running reuses the existing key.
    """

    kp = load_or_create_agent_keypair(agent_key_path)
    nonce = secrets.token_bytes(16)
    return OnboardingHandoff(
        agent_public_key=base64.b64encode(kp.public_bytes).decode("ascii"),
        hermes_node_id=hermes_node_id,
        onboarding_nonce=base64.b64encode(nonce).decode("ascii"),
        disclosure_profiles=DISCLOSURE_PROFILES,
    )


def render_qr_ascii(payload: str) -> str:
    """Render the handoff payload as an ASCII QR.

    v0 prints a placeholder banner with the payload. Real QR rendering uses
    the optional `qrcode` extra: ``pip install 'hearme-skill[qr]'`` then
    ``qrcode.make(payload).print_ascii()``.
    """

    try:
        import qrcode  # type: ignore

        qr = qrcode.QRCode(border=1)
        qr.add_data(payload)
        qr.make(fit=True)

        # qrcode's print_ascii writes to a stream; capture it.
        import io

        buf = io.StringIO()
        qr.print_ascii(out=buf)
        return buf.getvalue()
    except ModuleNotFoundError:
        return (
            "[install `qrcode` for real QR rendering; payload below]\n"
            f"{payload}\n"
        )


def accept_delegation_from_mock_phone(
    *,
    raw_json: str,
    delegation_path: Path,
) -> DelegationToken:
    """Accept a DelegationToken JSON from `scripts/mock-phone.py`.

    For dev only. The real flow accepts the same JSON shape from the
    QR-paired channel. Both paths land in the same on-disk format.
    """

    token = DelegationToken.model_validate_json(raw_json)
    store_delegation(delegation_path, token)
    return token
