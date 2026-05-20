# zkPassport → Self (self.xyz) migration plan

> **Status: design / docs-first.** This document is the agreed plan *before* code
> changes. `ARCHITECTURE.md` (§8) and `IDENTITY.md` already describe the target
> state; this file maps the concrete code work that follows. Nothing here is
> implemented yet.

## Why

See `IDENTITY.md`. Short version: Self has materially more adoption and longevity
(8–15M users; Google Cloud / Opera / Celo) than zkPassport ("not production-ready
for critical apps" per Safe research), **and** its SDK preserves Hearme's three
non-negotiables, verified against the real docs:

| Non-negotiable | Self mechanism | Verified |
|---|---|---|
| Off-chain verify, no Celo RPC at runtime | `@selfxyz/core` `SelfBackendVerifier.verify()` runs on our backend | ✅ |
| Bind agent key into the proof | `userDefinedData` (hex), committed via `userContextData`; returned by `verify()` | ✅ |
| Stable per-scope unique identifier | nullifier is `unique-per-user-per-scope` | ✅ |

## Decisions locked

1. **Replace zkPassport entirely.** Self is the sole personhood provider; no dual-provider path in v0.
2. **Region** ← disclosed `nationality`, mapped to region and **bucketed before storage** (raw country not persisted).
3. **Age** ← **multi-threshold ladder** at install (`older-than` proofs at `[18, 25, 35, 50, 65]`, shared scope ⇒ shared nullifier). **No DOB.** Only `18+` is required; finer thresholds optional → graceful fallback to `age_band="18+"`.

## Old → new mapping

| Area | zkPassport (old) | Self (new) |
|---|---|---|
| Package dir | `packages/zkpassport-bridge/` | `packages/self-bridge/` |
| Node SDK | `@zkpassport/sdk` + `@aztec/bb.js` | `@selfxyz/core` + `@selfxyz/qrcode` |
| Broker verify module | `verify/zkpassport.py` | `verify/self_identity.py` |
| Broker bridge client | `verify/bridge_client.py` | `verify/bridge_client.py` (repoint URL/shape) |
| Proto schema | `packages/proto/zkpassport.json` | `packages/proto/self.json` |
| Agent-key bind | SDK `custom_data` in `query` | `userDefinedData` (hex) in `userContextData` |
| Nullifier | `Poseidon2(id, domain, scope)` | Self nullifier, `unique-per-user-per-scope` |
| Scope | `domain="hearme.network"` + `scope="v1"` | single `scope="hearme-v1"` (≤31 ASCII) |
| Proof relay | relayed back via SDK request channel | Self app **POSTs to bridge `endpoint`** (`/callback`) |
| Token field | `zkpassport_proof` (single) | `self_proofs` (array; one per threshold) |
| Token `version` | `1` | `2` |
| Dev/test toggle | `ZKPASSPORT_DEV_MODE=1` | `SELF_MOCK_PASSPORT=1` (staging / Celo Sepolia) |

### Env vars

| Old | New |
|---|---|
| `ZKPASSPORT_DOMAIN`, `ZKPASSPORT_SCOPE` | `SELF_SCOPE` (=`hearme-v1`) |
| `ZKPASSPORT_DEV_MODE` | `SELF_MOCK_PASSPORT` |
| `ZKPASSPORT_VALIDITY_SECONDS` | (n/a — Self has no equivalent long validity window; revisit per-envelope freshness, see §13 verify-once) |
| `ZKPASSPORT_WRITING_DIR` | (drop — no bb.js CRS artifacts) |
| `HEARME_BROKER_ZKPASSPORT_BRIDGE_URL` | `HEARME_BROKER_SELF_BRIDGE_URL` |
| `HEARME_SKILL_ZKPASSPORT_BRIDGE_URL` | `HEARME_SKILL_SELF_BRIDGE_URL` |
| — | `SELF_ENDPOINT`, `SELF_ENDPOINT_TYPE`, `SELF_ALLOWED_IDS`, `SELF_AGE_THRESHOLDS` (new) |

## Per-component work

### 1. `packages/self-bridge` (rename + rewrite)
- Rename dir; swap deps to `@selfxyz/core` + `@selfxyz/qrcode`.
- `POST /requests {agentKey, profile}` → build SelfApp config(s) via `SelfAppBuilder` (scope, endpoint, `userDefinedData=hex(agentKey)`, disclosures `{nationality, minimumAge}`); return `{requestId, urls[]}` (one per threshold for `standard`).
- `POST /callback` → **the SelfApp endpoint**: receive `{attestationId, proof, publicSignals, userContextData}`, run `SelfBackendVerifier.verify()`, store result under `requestId`, return the app-expected ack.
- `GET /requests/:id` → return `{status, verified, uniqueIdentifier, disclosed, boundAgentKey, bundles[]}`.
- `POST /verify` → stateless re-verify of a stored bundle.
- See `packages/self-bridge/README.md` (already written) for the full endpoint/env spec.

### 2. `packages/broker`
- `verify/self_identity.py`: call bridge `/verify` per `self_proofs[]`; enforce bindings (agent_key == `userDefinedData`, scope, all proofs share one nullifier == `unique_identifier`); **re-derive** `region` (country→region) and `age_band` (older-than set→band) and **reject if they disagree with the token's `disclosed_predicates`**.
- Add pure helpers: `country_to_region()`, `thresholds_to_age_band()`.
- Nullifier registry: unchanged in spirit — register `unique_identifier`↔`agent_key`; reject a second agent_key for the same nullifier without revocation.
- Repoint `bridge_client.py` to `HEARME_BROKER_SELF_BRIDGE_URL` and the new request/response shapes.

### 3. `packages/skill` (onboarding)
- `onboarding.py`: call `/requests`, render each `url`, poll `/requests/:id` until all expected proofs complete.
- Build `DelegationToken` v2 with `self_proofs[]`, derive bucketed `disclosed_predicates` locally, store encrypted. Graceful fallback to `18+` if user completes only the required proof.
- `delegation.py`: load/validate v2 token.

### 4. `packages/proto`
- Replace `zkpassport.json` with `self.json` (verifiable Self bundle: `{attestationId, proof, publicSignals, userContextData}`).
- Update `delegation.json`: `version:2`, `self_proofs[]`, `scope`, drop `domain`/`zkpassport_proof`.

### 5. `docker-compose.yml`
- Rename service `zkpassport-bridge` → `self-bridge`; update `build.dockerfile`, `container_name`, env vars (table above), and the broker/skill `depends_on` + bridge-URL env.
- Update the header comment block and the mock-passport onboarding hint (`SELF_MOCK_PASSPORT=1`, staging).

### 6. `scripts/`
- `mock-onboard.py`: replay a captured Self proof fixture into a v2 token.
- Any `--bridge-url` defaults pointing at the renamed service.

## Database impact — minimal
- `envelopes.disclosed_predicates` JSONB keeps the same shape (`{age_band, region}`).
- `envelopes.unique_identifier` semantics unchanged (now a Self nullifier string).
- `delegation_hash` / `agent_signature` schemes unchanged.
- **No migration of existing rows** (v0, no production data). New onboardings issue v2 tokens.

## Testing changes (ARCHITECTURE §12)
- Unit: mock the bridge with a canned `VerificationResult`; assert binding + predicate-derivation rejections.
- New `test_predicate_derivation.py`: country→region, thresholds→age_band (boundaries, unmapped country, partial threshold set → `18+`).
- E2E: swap `self-bridge` into the compose stack; onboard with a mock passport (`SELF_MOCK_PASSPORT=1`, staging) or a captured fixture; assert the boundary-leakage check still holds (envelope has exactly the 5 fields).

## Open items to confirm against the real SDK during implementation
1. **`userDefinedData` byte budget** — confirm it holds a 32-byte Ed25519 key (64 hex chars). If capped below that, bind via `userId` or a hash of the key instead.
2. **Re-verifiability** — confirm `SelfBackendVerifier.verify()` is safely re-runnable on a stored `(proof, publicSignals, userContextData)` (needed for per-envelope re-verify). If proofs are single-use/freshness-bound, jump straight to the §13 verify-once + session-credential model.
3. **Multi-proof session UX** — confirm the cleanest way to request several thresholds (sequential SelfApp requests vs one batched flow) and that all share the nullifier under one scope.
4. **Attestation IDs** — confirm `AllIds` / which `attestationId`s to allow (passport vs EU ID card vs Aadhaar) and set `SELF_ALLOWED_IDS` accordingly.
5. **Supported Node version** for `@selfxyz/core`; pin the version (experimental SDK).
6. **Registry/merkle root** — confirm the off-chain verifier does not require live Celo registry membership reads (docs say no RPC); document the residual trust (IDENTITY.md caveat 5).

## Sequencing
1. Land these docs (this PR).
2. Build `self-bridge` + its tests (network-free smoke, then a live staging verify behind a flag).
3. Broker `self_identity.py` + predicate helpers + tests.
4. Skill onboarding v2 + proto.
5. Compose + scripts + E2E.
6. Flip ARCHITECTURE §11 item to **DONE**; delete the `zkpassport-bridge` dir.
