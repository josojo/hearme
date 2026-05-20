# zkPassport → Self (self.xyz) migration plan

> **Status: design / docs-first.** This document is the agreed plan *before* code
> changes. `ARCHITECTURE.md` and `IDENTITY.md` describe the target state; this file
> maps the concrete code work that follows. Nothing here is implemented yet.

## Why

See `IDENTITY.md`. Short version: Self has materially more adoption and longevity
(8–15M users; Google Cloud / Opera / Celo) than zkPassport ("not production-ready
for critical apps" per Safe research), **and** its SDK preserves Hearme's three
non-negotiables, verified against the real docs:

| Non-negotiable | Self mechanism | Verified |
|---|---|---|
| Off-chain verify, no Celo RPC at runtime | `@selfxyz/core` `SelfBackendVerifier.verify()` runs on our backend | ✅ |
| Bind agent key into the proof | `userDefinedData` (variable-length `bytes`), committed via `userContextData`; returned by `verify()` | ✅ |
| Stable per-scope unique identifier | nullifier is `unique-per-user-per-scope` | ✅ |

## Decisions locked

1. **Replace zkPassport entirely.** Self is the sole personhood provider; no dual-provider path in v0.
2. **Region** ← disclosed `nationality`, mapped to region and **bucketed at registration** (raw country not persisted).
3. **Age** ← **multi-threshold ladder** at install (`older-than` proofs at `[18, 25, 35, 50, 65]`, shared scope ⇒ shared nullifier). **No DOB.** Only `18+` required; finer thresholds optional → graceful fallback to `age_band="18+"`.
4. **Verify-once-at-registration + broker-issued session credential.** **This is forced, not optional:** Self proofs expire **±1 day** (`SelfBackendVerifier` throws `InvalidTimestamp`), so the broker cannot re-verify a stored proof per envelope over a 90-day token. The broker verifies the proofs **once** at `POST /v1/register`, then issues a **broker-signed `DelegationToken`** the agent replays per answer. The raw proof never travels per answer (also removes per-envelope SNARK cost and closes the §1.2 transit gap). The `DelegationToken` is **redefined**: it is now the broker-issued credential, not a phone-side bundle of proofs.

## Old → new mapping

| Area | zkPassport (old) | Self (new) |
|---|---|---|
| Package dir | `packages/zkpassport-bridge/` | `packages/self-bridge/` |
| Node SDK | `@zkpassport/sdk` + `@aztec/bb.js` | `@selfxyz/core` + `@selfxyz/qrcode` |
| Broker SNARK verify | `verify/zkpassport.py` (per envelope) | `verify/self_identity.py` (**registration only**) |
| Broker bridge client | `verify/bridge_client.py` (per envelope) | `verify/bridge_client.py` (**registration only**) |
| Agent-key bind | SDK `custom_data` in `query` | `userDefinedData` in `userContextData` |
| Nullifier | `Poseidon2(id, domain, scope)` | Self nullifier, `unique-per-user-per-scope` |
| Scope | `domain="hearme.network"` + `scope="v1"` | single `scope="hearme-v1"` (≤31 ASCII) |
| Proof relay | relayed back via SDK request channel | Self app **POSTs to bridge `endpoint`** (`/callback`) |
| **Verification timing** | **per envelope** (re-verify proof) | **once at registration** (Self ±1 day window forbids per-envelope) |
| **Per-envelope artifact** | DelegationToken embeds the raw proof(s) | DelegationToken = **broker-signed credential** (no proof) |
| **Install→broker payload** | (none; token built client-side) | **EnrollmentBundle** `{self_proofs[], agent_key}` → `POST /v1/register` |
| Token `version` | `1` | `2` |
| Dev/test toggle | `ZKPASSPORT_DEV_MODE=1` | `SELF_MOCK_PASSPORT=1` (staging / Celo Sepolia) |
| **New endpoint** | — | `POST /v1/register` |
| **New table** | — | `registrations` (nullifier registry; see below) |
| **New broker secret** | — | `broker_key` (Ed25519; signs the DelegationToken) |

### Env vars

| Old | New |
|---|---|
| `ZKPASSPORT_DOMAIN`, `ZKPASSPORT_SCOPE` | `SELF_SCOPE` (=`hearme-v1`) |
| `ZKPASSPORT_DEV_MODE` | `SELF_MOCK_PASSPORT` |
| `ZKPASSPORT_VALIDITY_SECONDS` | **(drop)** — Self proofs are ±1 day; freshness is irrelevant after verify-once |
| `ZKPASSPORT_WRITING_DIR` | (drop — no bb.js CRS artifacts) |
| `HEARME_BROKER_ZKPASSPORT_BRIDGE_URL` | `HEARME_BROKER_SELF_BRIDGE_URL` |
| `HEARME_SKILL_ZKPASSPORT_BRIDGE_URL` | `HEARME_SKILL_SELF_BRIDGE_URL` |
| — | `SELF_ENDPOINT`, `SELF_ENDPOINT_TYPE`, `SELF_ALLOWED_IDS`, `SELF_AGE_THRESHOLDS` (new) |
| — | `HEARME_BROKER_SIGNING_KEY` (the `broker_key`; v0 from config/secret) |

## Per-component work

### 1. `packages/self-bridge` (rename + rewrite)
- Rename dir; swap deps to `@selfxyz/core` + `@selfxyz/qrcode`.
- `POST /requests {agentKey, profile}` → build SelfApp config(s) via `SelfAppBuilder` (scope, endpoint, `userDefinedData=hex(agentKey)`, disclosures `{nationality, minimumAge}`); return `{requestId, urls[]}` (one per threshold for `standard`).
- `POST /callback` → **the SelfApp endpoint**: receive `{attestationId, proof, publicSignals, userContextData}`, run `SelfBackendVerifier.verify()`, store result under `requestId`, return the app-expected ack.
- `GET /requests/:id` → return `{status, verified, uniqueIdentifier, disclosed, boundAgentKey, bundles[]}`.
- `POST /verify` → stateless verify of a bundle. **Called only by the broker at registration**, not per envelope.
- See `packages/self-bridge/README.md` (already written) for the full endpoint/env spec.

### 2. `packages/broker`
- **`routes/register.py`** (new) → `POST /v1/register`: the registration pipeline (ARCHITECTURE §5).
- **`verify/self_identity.py`**: call bridge `/verify` per `self_proofs[]`; enforce bindings (agent_key == `userDefinedData`, scope, all proofs share one nullifier == `unique_identifier`); **derive** `region`/`age_band` (broker is authoritative).
- **`verify/credential.py`** (new): hold the `broker_key`; `issue(token_claims) -> broker_signature`; `verify(delegation_token)`.
- **`verify/delegation.py`**: per-envelope only — verify `broker_signature`, expiry, and registry/revocation (`registrations` lookup). **No bridge call.**
- Pure helpers: `country_to_region()`, `thresholds_to_age_band()`.
- Registry: `INSERT registrations(...)` atomically; reject a second agent_key for an already-bound nullifier (Sybil); idempotent for the same agent_key (refresh).
- `bridge_client.py` → `HEARME_BROKER_SELF_BRIDGE_URL`, new request/response shapes.

### 3. `packages/skill` (onboarding)
- `onboarding.py`: call self-bridge `/requests`, render each `url`, poll `/requests/:id` until all expected proofs complete; assemble the **EnrollmentBundle** `{self_proofs[], agent_key}`; `POST /v1/register`; store the **broker-issued DelegationToken** encrypted; discard the raw proofs. Graceful fallback to `18+`.
- `delegation.py`: load/validate the broker-issued v2 token; treat it as opaque (don't re-derive predicates client-side).

### 4. `packages/proto`
- `enrollment.json` (new): `{self_proofs[], agent_key}`.
- `self.json` (replaces `zkpassport.json`): verifiable Self bundle `{attestationId, proof, publicSignals, userContextData}`.
- `delegation.json`: rewrite to the **broker-issued credential** — `version:2`, `scope`, `unique_identifier`, `disclosed_predicates`, `agent_key`, `issued_at`, `expires_at`, `broker_signature`. Drop `self_proofs`/`domain`.

### 5. Database migration (`packages/web/drizzle`)
- **New `registrations` table** (ARCHITECTURE §3): `unique_identifier PK, agent_key, disclosed_predicates JSONB, issued_at, expires_at, revoked_at`. Grant the broker role write access.
- `envelopes` unchanged in shape (`disclosed_predicates`, `unique_identifier`, `delegation_hash` semantics carry over; `delegation_hash` now hashes the broker-issued token).
- No row migration (v0, no production data).

### 6. `docker-compose.yml`
- Rename service `zkpassport-bridge` → `self-bridge`; update `build.dockerfile`, `container_name`, env vars (table above), broker/skill `depends_on` + bridge-URL env, and add `HEARME_BROKER_SIGNING_KEY`.
- Update the header comment and the mock-passport onboarding hint (`SELF_MOCK_PASSPORT=1`, staging).

### 7. `scripts/`
- `mock-onboard.py`: replay a captured Self proof fixture **through `POST /v1/register`** to obtain a broker-issued token.
- `--bridge-url` defaults → renamed service.

## Testing changes (ARCHITECTURE §12)
- **Registration**: mock the bridge with a canned `VerificationResult`; assert binding rejections, `InvalidTimestamp`/expired-proof rejection, and the Sybil bind (second nullifier+different-key rejected).
- **Credential** (`credential.py`): sign/verify round-trip; tampered claim or non-broker key rejected.
- **Predicate derivation** (`test_predicate_derivation.py`): country→region, thresholds→age_band (boundaries, unmapped country, partial set → `18+`).
- **Verify envelope**: expired/revoked/unknown registration, signature swaps; **assert the bridge client is never called on this path**.
- **E2E**: onboard via `/v1/register` (mock passport, staging, or fixture) → assert a `registrations` row; then assert the self-bridge is hit **zero** times during `/v1/envelopes`, and the envelope body carries no `self_proofs`.

## Open items — status after research

| # | Item | Status |
|---|---|---|
| 1 | `userDefinedData` byte budget for a 32-byte key | ✅ **Resolved** — variable-length `bytes`, no documented cap; 32 bytes fits. Confirm empirically; fallback = bind a hash. |
| 2 | `verify()` re-runnable per envelope | ⛔ **Resolved against it** — proofs expire ±1 day → **drove the verify-once design** (decision 4). |
| 3 | Multi-proof onboarding UX | ⚠️ **Mostly resolved** — passport scanned **once** (identity cached), then N proof round-trips (no batching: one disclosure config per proof). Chain the deeplinks; prototype latency on a real device. |
| 4 | Attestation IDs to allow | ⏳ Confirm `AllIds` (passport vs EU ID card vs Aadhaar) → set `SELF_ALLOWED_IDS`. |
| 5 | Supported Node version for `@selfxyz/core` | ⏳ Confirm + pin (experimental SDK). |
| 6 | Off-chain registry/merkle trust | ⏳ Docs say no RPC; verifier does not consult Celo's live registry → document residual trust (IDENTITY.md caveat 5). |

## Sequencing
1. Land these docs (this PR).
2. DB migration: add `registrations` + grants.
3. Build `self-bridge` + tests (network-free smoke, then a live staging verify behind a flag).
4. Broker: `self_identity.py`, `credential.py` (+ `broker_key`), `routes/register.py`, per-envelope `delegation.py`, predicate helpers + tests.
5. Skill onboarding (EnrollmentBundle → `/v1/register`) + proto.
6. Compose + scripts + E2E.
7. Flip ARCHITECTURE §11 item to **DONE**; delete the `zkpassport-bridge` dir.
