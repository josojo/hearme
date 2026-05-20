"""Broker runtime configuration.

Environment-driven. The DATABASE_URL points at the shared Postgres using the
``hearme_broker`` role (see /db/init/02-roles.sql and the README).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dev-only Ed25519 seed for the broker signing key (base64 of 32 bytes).
# Production MUST override HEARME_BROKER_SIGNING_KEY with a secret-managed key;
# a stable key is required so DelegationTokens survive broker restarts.
_DEV_BROKER_SIGNING_KEY = "QlJPS0VSLVNJR05JTkctS0VZLUhFQVJNRS1ERVYzMkI="  # b"BROKER-SIGNING-KEY-HEARME-DEV32B"


class Settings(BaseSettings):
    """Broker settings.

    Defaults match the docker-compose dev environment so a fresh `dev-up.sh`
    can `uvicorn` straight out of the box.
    """

    model_config = SettingsConfigDict(env_prefix="HEARME_BROKER_", extra="ignore")

    database_url: str = Field(
        default="postgres://hearme_broker:hearme_broker_dev@localhost:5432/hearme",
        description="asyncpg-compatible DSN scoped to the hearme_broker role.",
    )
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10
    # v0 returns detailed rejection reasons to help integration. Production
    # should set this False (avoid being an oracle — see ARCHITECTURE.md §5).
    expose_rejection_reasons: bool = True

    # self-bridge: the Node sidecar that runs @selfxyz/core's SelfBackendVerifier
    # (off-chain SNARK) plus the one-time on-chain Celo registry/root check. The
    # broker calls it ONLY at POST /v1/register (verify-once); never per envelope.
    # Point this at a bridge instance the broker controls.
    self_bridge_url: str = Field(
        default="http://localhost:8787",
        description="Base URL of the self-bridge POST /verify endpoint.",
    )
    self_verify_timeout_seconds: float = 30.0

    # Sybil hardening (ARCHITECTURE.md §5): require the bridge's one-time on-chain
    # registry/Merkle-root confirmation at registration. Default True (prod).
    # Dev/staging without a wired Celo RPC may set this False (documented risk).
    require_registry_confirmation: bool = True

    # Ed25519 signing key (base64 of a 32-byte seed) the broker uses to sign the
    # DelegationToken it issues at registration. The agent treats the token as
    # opaque; only the broker validates it. MUST be overridden in production.
    broker_signing_key: str = Field(
        default=_DEV_BROKER_SIGNING_KEY,
        description="base64 of the 32-byte Ed25519 seed for the broker signing key.",
    )


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
