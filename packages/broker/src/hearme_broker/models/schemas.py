"""Pydantic models for the broker wire formats.

Mirror packages/proto/{delegation,envelope,question}.json. `extra="forbid"`
matches the boundary-leakage assertion in ARCHITECTURE.md §12: an envelope
body MUST contain exactly five top-level fields.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DelegationToken(BaseModel):
    """Phone-issued bundle authorizing an agent_key to speak for a user.

    Canonical-JSON of this object is the input to
    ``delegation_hash = SHA-256(canonical_json(token))``.
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    zkpassport_proof: str = Field(description="base64 zkPassport proof bytes")
    domain: Literal["hearme.network"]
    scope: Literal["v1"]
    unique_identifier: str = Field(description="base64, 32 bytes")
    disclosed_predicates: dict[str, str]
    agent_key: str = Field(description="base64 Ed25519 public key, 32 bytes")
    issued_at: datetime
    expires_at: datetime
    phone_signature: str = Field(description="base64 Ed25519 signature, 64 bytes")


class Envelope(BaseModel):
    """POST /v1/envelopes body. Exactly 5 fields — boundary-leakage check."""

    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    answer: str
    nonce: str
    delegation_token: DelegationToken
    agent_signature: str = Field(description="base64 Ed25519 signature, 64 bytes")


class Question(BaseModel):
    """GET /v1/questions/open row."""

    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    text: str
    topic: str | None = None
    created_at: datetime
    closes_at: datetime
    nonce: str


class RejectionReason(str, Enum):
    """Specific reasons the broker rejects an envelope.

    Returned in the ack body when ``expose_rejection_reasons`` is True (v0
    default for debugging). Production should set this False so the broker
    is not a verification oracle (ARCHITECTURE.md §5).
    """

    SCHEMA_INVALID = "schema_invalid"
    PHONE_SIGNATURE_INVALID = "phone_signature_invalid"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_REVOKED = "token_revoked"
    DELEGATION_HASH_MISMATCH = "delegation_hash_mismatch"
    AGENT_SIGNATURE_INVALID = "agent_signature_invalid"
    AGENT_KEY_INVALID = "agent_key_invalid"
    QUESTION_NOT_FOUND = "question_not_found"
    QUESTION_NOT_OPEN = "question_not_open"
    QUESTION_CLOSED = "question_closed"
    NONCE_MISMATCH = "nonce_mismatch"
    SCOPE_INELIGIBLE = "scope_ineligible"
    DUPLICATE = "duplicate"
    INTERNAL_ERROR = "internal_error"


class EnvelopeAck(BaseModel):
    """Response to POST /v1/envelopes."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    reason: RejectionReason | None = None
