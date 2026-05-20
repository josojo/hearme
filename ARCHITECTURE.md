# Hearme — v0 Architecture

Three components wired together:
1. **`hearme-web`** — Next.js site where askers post questions and anyone can see how agents answered.
2. **`hearme-broker`** — Python service that dispatches questions to agents, verifies returned envelopes, and is the only writer to the answers table.
3. **`hearme-skill`** — Python skill that runs inside a user's Hermes Agent and answers questions on their behalf.

Plus a shared Postgres database, and the user's phone (running the **Self** app, [self.xyz](https://self.xyz)) which appears only at install/refresh time.

> **Identity provider: Self (self.xyz).** Hearme's proof-of-personhood layer is built on Self — passport/national-ID NFC + zk-SNARKs. Proofs are SNARK-verified **off-chain** on our own backend; the **only** on-chain dependency is a single Celo Identity-Registry read **at registration** (§5, Sybil hardening). Per answer there is **no chain access and no proof at all** (§1.5). This replaced an earlier zkPassport integration; see `IDENTITY.md` for the why and §8 for the concrete flow.

## 1. Design principles

These are the non-negotiables. Every component below exists to serve one of them.

### 1.1 Consent is the product
The agent answers *on behalf of* the user. If users ever feel surveilled, Hearme dies. The skill must expose a sharp, legible policy surface (topics, askers, daily caps, payment floor) and never silently drift from it. Default to off; opt-in per category.

### 1.2 Personal-data minimization at the boundary
The agent reasons over rich personal memory locally (or with help of a model provider). Only the **answer itself** plus the user's **DelegationToken** — a **broker-issued, broker-signed session credential** carrying a stable `uniqueIdentifier`, the bucketed predicates, and the bound `agent_key` — crosses the device + model boundary. Raw facts, chain-of-thought, source memories, raw passport fields, and the raw Self proofs — never.

> **Why a broker-issued credential (not the raw proof).** Self proofs expire **±1 day** (`SelfBackendVerifier` throws `InvalidTimestamp` outside that window), so the broker *cannot* re-verify a stored proof per envelope over a 90-day token. Hearme therefore **verifies the Self proofs exactly once, at registration** (§8.1), and the broker issues a signed session credential the agent replays per answer (§5). This is not just a performance choice — it is forced by Self's freshness window. It also closes the data-minimization boundary: the raw proof (and the raw nationality inside it) reaches the broker **once at registration**, where it is bucketed (`region`, `age_band`) and the raw form discarded; per-answer, only the bucketed credential travels.

### 1.3 Predicate disclosure, fixed at install
Demographic disclosure is decided **once**, at install, when the user picks a disclosure level on the phone (e.g. age band, region). The chosen predicates are proven via Self, verified once by the broker at registration, and baked into the broker-issued DelegationToken. Every answer reuses the same predicate set; askers do **not** negotiate predicates per question. If an asker needs finer slicing, they slice post-hoc on the aggregate, not by demanding new disclosures from the user.

### 1.4 Sybil resistance via stable scoped uniqueness; linkability is bounded and named
The DelegationToken's `uniqueIdentifier` is the **Self nullifier** under the single scope `"hearme-v1"` (Self collapses domain + scope into one ≤31-ASCII scope string; the nullifier is `unique-per-user-per-scope`) — so the same passport produces the same identifier across every Hearme answer. The broker uses this for one-answer-per-`(question_id, uniqueIdentifier)` enforcement and for per-user honeypot scoring. This means **the broker can link a user's answers to each other** within Hearme. This is a deliberate v0 tradeoff: it buys "zero time cost per question" (no phone round-trip), and the broker is contractually bound to publish only aggregates. Epoch-rotated scopes (so identifiers rotate weekly/monthly) are a v0.2 upgrade documented in §13.

### 1.5 Verify all, trust none (broker side)
The broker treats every envelope as potentially malicious. Verification is split in two:

- **Once, at registration (`POST /v1/register`, §8.1):** the broker runs the real SNARK check on the Self proof set via the **self-bridge**, **confirms the proof's Merkle root against Self's live on-chain Identity Registry on Celo** (the one and only on-chain read — see §5; it proves the proof was built against the real registry, where one-passport→one-identity is enforced), enforces the bindings (agent_key ↔ `userDefinedData`, scope, one shared nullifier), re-derives the bucketed predicates, atomically binds `nullifier ↔ agent_key` in the registry, and issues a **broker-signed DelegationToken**.
- **Per envelope (`POST /v1/envelopes`):** the broker verifies *its own* signature on the DelegationToken, the token's expiry, the registry/revocation status, the agent's per-question signature, the request linkage, and the uniqueness constraint — every time. **No bridge call, no Self proof, no raw passport data** at answer time.

There is no phone signature on the token; registration integrity comes from the SNARK, per-answer integrity from the broker's signature. The frontend never sees raw envelopes; it sees only verified writes.

### 1.6 Coercion resistance
The skill must never emit a side-channel artifact (signed receipt, plaintext log shipped off-device, screenshot to cloud) that lets a third party prove how the user answered. The user gets a local audit trail. Nobody else does.

### 1.7 Indistinguishable response fidelity
Hearme plants honeypot questions to catch lazy agents. The skill must answer real and test questions with identical depth. No "is this a test?" branches — that defeats the mechanism.

### 1.8 Local-first decisioning
All policy evaluation, persona projection, and answer generation runs in-process inside the user's Hermes instance and model provider.

### 1.9 Idempotent and replay-safe
Networks fail; brokers retry. Every question carries an ID. Answering the same `question_id` twice is a no-op. Every envelope includes a per-question agent signature over `(question_id, answer, nonce, delegation_hash)` so envelopes can't be replayed against a different `question_id`.

### 1.10 Time-boxed
Questions have a validity window. Stale questions are dropped, not answered late.

### 1.11 Memory-provider agnostic
Hermes supports 8 memory backends. The skill talks through Hermes's memory abstraction; it never imports a specific provider.

### 1.12 Override is sacred
The user can preview, edit, or veto any answer before submission. Every submitted answer is revocable post-hoc within the protocol's revocation window.

### 1.13 Phone is the enrollment device, not a hot dependency
The user's phone (running the Self app) is touched at exactly three moments: **install**, **refresh** (every 90 days), and **revocation**. Because age granularity uses a multi-threshold scheme (§8.3), *install* may run several quick Self proofs back-to-back; this cost is paid once and isolated to these three moments. In steady state, the phone is never contacted.

### 1.14 Cheap relevance gating before generation

**Problem.** Most users have no formed view on most questions. The economics in VISION.md set the per-response payout at roughly the cost of one LLM inference (~a fraction of a cent). If the skill runs a full generation just to discover the user has no signal on a topic, the marginal answer is worth less than its inference cost — the platform burns budget producing noise and the buyer pays for it. At scale, this inverts the unit economics of the whole marketplace.

**Strategy.** The cost of an answer is not a single number. A retrieval-tier embedding lookup over the user's memory is roughly **100–1000× cheaper** than a generation-tier LLM call. The skill MUST exploit this asymmetry: before invoking the Answerer, run a cheap relevance check (§7.3). If the user has no relevant memory above threshold, emit a `no_signal` envelope and skip generation entirely. The no-signal branch drops from ~$0.001 (full inference) to ~$0.00001 (one embedding lookup).

**Implication.** `no_signal` is not noise — it is real aggregate data ("47% of EU 25–34 respondents had no formed view on synthetic meat") and it is exactly the silent-majority finding that traditional Likert-forced polls hide. Aggregation MUST treat `no_signal` as a first-class bucket, not a discarded row. Honeypots (VISION.md Challenge #6) still apply: an agent that emits `no_signal` on a planted test question fails just as hard as one that fakes an opinion, because the planted instruction is detectable at the retrieval tier too. `no_signal` is not rewarded with the full reward/payout. Honeypots questions that are answered with `no_signal` are never punished.

---

## 2. v0 system overview

```
┌────────────────────┐        ┌─────────────────────────────┐
│  Asker (browser)   │        │  Curious public (browser)   │
└─────────┬──────────┘        └──────────────┬──────────────┘
          │ POST question                    │ GET question/aggregate
          │                                  │
          ▼                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  hearme-web  (Next.js, App Router, server components)       │
│  - reads: questions, aggregates                             │
│  - writes: questions (only)                                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ SQL (read mostly)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Postgres  (shared)                                         │
│  questions │ envelopes │ aggregates │ askers │ revocations  │
└────────────▲──────────────────────────────▲─────────────────┘
             │ write envelopes              │ poll for open questions
             │ increment aggregates         │
┌────────────┴───────┐               ┌──────┴─────────────────┐
│  hearme-broker     │   HTTP/JSON   │  hearme-skill          │
│  (Python/FastAPI)  ├──────────────►│  (Python, in Hermes)   │
│                    │◄──────────────┤                        │
│  - dispatches Qs   │  envelopes    │  - answers Qs locally  │
│  - verifies        │               │  - stamps DelegationTok│
│    envelopes       │               │  - signs per question  │
└────────────────────┘               └────────────┬───────────┘
                                                  ▲
                                                  │ install + refresh only
                                                  │
                                     ┌────────────┴───────────┐
                                     │  User phone — Self app │
                                     └────────────────────────┘
```

**Boundaries.** The frontend and the broker share a database but not code; they communicate only through Postgres. The broker is the only service that can write `envelopes` rows (enforced by DB role grants). The frontend is the only service that creates `questions`. Agents never talk to the frontend; they only talk to the broker.

**Why three services and not one.** The broker's verification logic is security-critical and must be reviewable in isolation. Bundling it into Next.js API routes would tangle it with UI concerns. Keeping it as a separate Python service lets it share verification code with `hearme-skill` and lets us deploy/scale them differently later.

---

## 3. Shared database

Postgres. Schema is owned by `hearme-web` (Drizzle migrations live in that repo) but both services read from it; the broker has its own role with write permission scoped to `envelopes`, `aggregates`, `revocations`, `registrations`.

```sql
CREATE TABLE askers (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name  TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE questions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  asker_id    UUID REFERENCES askers(id),
  text        TEXT NOT NULL,
  topic       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  closes_at   TIMESTAMPTZ NOT NULL,
  status      TEXT NOT NULL DEFAULT 'open'   -- 'open' | 'closed'
);

CREATE TABLE envelopes (
  question_id          UUID NOT NULL REFERENCES questions(id),
  unique_identifier    TEXT NOT NULL,              -- from DelegationToken, stable per user
  answer               TEXT NOT NULL,              -- LLM-generated answer text (empty string when no_signal=true)
  no_signal            BOOLEAN NOT NULL DEFAULT FALSE, -- §1.14 / §7.3: agent had no relevant memory; skipped generation
  relevance_score      REAL NOT NULL,              -- §7.3: top-k embedding similarity vs user memory, in [0, 1]
  disclosed_predicates JSONB NOT NULL,             -- {age_band, region, ...}
  agent_signature      TEXT NOT NULL,              -- base64 Ed25519 (agent_key over the per-question payload)
  delegation_hash      TEXT NOT NULL,              -- hash of the broker-issued DelegationToken used
  submitted_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (question_id, unique_identifier)     -- 1 answer per human per question
);

-- Nullifier registry: written once per identity at POST /v1/register (§8.1).
-- Enforces one agent_key per Self nullifier (atomic Sybil bind) and backs
-- the broker-issued session credential (DelegationToken).
CREATE TABLE registrations (
  unique_identifier    TEXT PRIMARY KEY,           -- Self nullifier (scope "hearme-v1")
  agent_key            TEXT NOT NULL,              -- base64 Ed25519 pubkey bound to this nullifier
  disclosed_predicates JSONB NOT NULL,             -- bucketed {age_band, region} re-derived at registration
  issued_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at           TIMESTAMPTZ NOT NULL,       -- credential TTL (default issued_at + 90 days)
  revoked_at           TIMESTAMPTZ                 -- NULL unless revoked
);

CREATE TABLE aggregates (
  question_id    UUID PRIMARY KEY REFERENCES questions(id),
  total_answers  INTEGER NOT NULL DEFAULT 0,
  by_predicate   JSONB NOT NULL DEFAULT '{}',       -- {"region:EU": 42, ...}
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE revocations (
  delegation_hash TEXT PRIMARY KEY,
  revoked_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON envelopes(question_id);
CREATE INDEX ON envelopes(submitted_at);
```

The composite primary key on `envelopes(question_id, unique_identifier)` is the hard enforcement of Sybil resistance at the database layer. The broker can crash, restart, double-submit — the DB still rejects duplicates.

---

## 4. `hearme-web` — frontend

Next.js App Router. Server components for reads; client components only where interactivity demands it.

**Stack.**
- Next.js 14+ (App Router)
- TypeScript
- Drizzle ORM
- Postgres
- Tailwind for styling

**Pages.**
- `/` — list of recent open questions with answer counts. Server component, queries Postgres directly.
- `/ask` — form to create a question. Server action submits and redirects to the question detail page.
- `/q/[id]` — question detail. Shows the question text, total answer count, a breakdown by predicate (e.g. "EU: 42, non-EU: 18"), and a paginated list of individual answers with their disclosed predicates. Polls every 10s for new envelopes (or uses `revalidate` + a refresh button — TBD).

**What it does NOT do.**
- No auth in v0. Askers identify by display name only.
- No payments. No payment fields in the UI.
- No envelope writes. The frontend cannot create or modify envelopes; the DB role used by Next.js doesn't have `INSERT` on `envelopes` or `aggregates`.
- No direct talking to agents. Everything goes via the database, which the broker writes.

**Layout.**

```
hearme-web/
├── package.json
├── next.config.js
├── drizzle.config.ts
├── drizzle/                      # migrations
├── src/
│   ├── app/
│   │   ├── page.tsx              # /
│   │   ├── ask/page.tsx          # /ask
│   │   ├── q/[id]/page.tsx       # /q/[id]
│   │   └── layout.tsx
│   ├── db/
│   │   ├── client.ts             # Drizzle client
│   │   └── schema.ts             # shared with broker via codegen or hand-mirror
│   ├── actions/
│   │   └── create-question.ts    # server action
│   └── components/
│       ├── question-card.tsx
│       ├── ask-form.tsx
│       └── aggregate-chart.tsx
└── README.md
```

---

## 5. `hearme-broker` — dispatcher and verifier

Python service. Single binary. Two responsibilities: dispatch open questions to agents, and verify+persist envelopes that come back.

**Stack.**
- Python 3.11+
- FastAPI (HTTP + optional WebSocket later)
- asyncpg (Postgres)
- pynacl (Ed25519 signatures)
- Pydantic v2 (schema validation)

**HTTP API.**
- `GET /v1/questions/open?since=<iso8601>` — agents poll for new open questions. Returns:
  ```json
  [
    {
      "question_id": "uuid",
      "text": "...",
      "topic": "...",
      "created_at": "2026-05-19T12:00:00Z",
      "closes_at": "2026-05-20T12:00:00Z",
      "nonce": "<random_per_question>"
    }
  ]
  ```
- `POST /v1/register` — agents enroll once at install. Body is the **enrollment bundle** `{self_proofs[], agent_key}` (see §8.5). The broker SNARK-verifies the proofs via the self-bridge, binds `nullifier ↔ agent_key`, and returns the broker-issued **DelegationToken** (the session credential) or `{accepted: false, reason}`. Idempotent: re-registering the same `(nullifier, agent_key)` re-issues a fresh token; a *different* agent_key for an already-bound nullifier is rejected (Sybil).
- `POST /v1/envelopes` — agents submit answers. Body is the envelope (see §8.5). Returns `{accepted: true}` or `{accepted: false, reason}`.
- `GET /healthz` — liveness.

For v0, simple HTTP polling is fine. Long-poll or WebSocket is a v0.2 transport upgrade.

**Registration pipeline (once, `POST /v1/register`).** The only path that touches a Self proof.

```
parse enrollment bundle (pydantic): {self_proofs[], agent_key}
  → for each self_proof: verify real SNARK via the self-bridge (@selfxyz/core)
       (rejects if proof invalid OR timestamp outside Self's ±1 day window)
  → ON-CHAIN REGISTRY CHECK (registration only, one Celo RPC read via the self-bridge):
       confirm each proof's identity-registry Merkle root is a CURRENT/known root
       published by Self's on-chain Identity Registry / Hub on Celo, AND the identity
       is registered. This is what makes the off-chain SNARK trustworthy: it proves the
       proof was built against the REAL Self registry (where one-passport→one-identity is
       enforced), not a forged/stale tree an attacker assembled. Reject if the root is
       unknown/stale, the identity is not registered, or the RPC is required-but-unreachable.
       (This is the ONLY on-chain read in the system, and it happens once per identity.)
  → enforce bindings: agent_key == userDefinedData, scope == "hearme-v1",
       all proofs carry the SAME nullifier  → unique_identifier
  → re-derive region (from disclosed nationality) and age_band (from the older-than
       booleans across the proofs) — the broker's value is authoritative
  → atomic registry bind:
       INSERT registrations(unique_identifier, agent_key, disclosed_predicates, expires_at)
       — if nullifier already bound to a DIFFERENT agent_key (and not revoked): reject
  → issue DelegationToken: broker_signature = Sign(broker_key, H(canonical_json(claims)))
  → return the DelegationToken
```

**Verification pipeline (per envelope, `POST /v1/envelopes`).** No bridge call, no Self proof.

```
parse (pydantic)
  → verify broker_signature on delegation_token using the broker's own pubkey
  → check token.expires_at > now()
  → check registrations[token.unique_identifier] exists, agent_key matches, revoked_at IS NULL
  → recompute expected delegation_hash and compare
  → verify agent_signature over H(question_id, answer, nonce, delegation_hash) using token.agent_key.public
  → check question_id exists, status='open', closes_at > now()
  → check signed predicates are eligible for the question scope
  → INSERT envelope (UNIQUE constraint rejects duplicates)
  → increment aggregates row for question_id
```

If any step fails, the request is rejected with a specific reason code; nothing is written. Reasons are logged but **not** returned in detail to the agent in production (avoid an oracle); v0 returns detailed reasons for debugging.

**Question dispatch.**
- Broker doesn't push; agents poll `/v1/questions/open?since=last_poll`.
- Each agent tracks its own `last_poll` locally from the max broker-supplied
  `created_at` it has seen, not from the agent host's wall clock.
- No per-agent *dispatch* state on the broker (the `registrations` registry is identity state, written once at enrollment, not per question). Restart-safe either way.

**Layout.**

```
hearme-broker/
├── pyproject.toml
├── src/hearme_broker/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app
│   ├── routes/
│   │   ├── questions.py          # GET /v1/questions/open
│   │   ├── register.py           # POST /v1/register  (registration pipeline)
│   │   └── envelopes.py          # POST /v1/envelopes (per-envelope pipeline)
│   ├── verify/
│   │   ├── __init__.py
│   │   ├── self_identity.py      # registration: real SNARK check (via bridge) + bindings + predicate derivation
│   │   ├── bridge_client.py      # HTTP client for the self-bridge (registration only)
│   │   ├── credential.py         # issue + verify the broker-signed DelegationToken; broker keypair
│   │   ├── delegation.py         # per-envelope: token signature + expiry + registry/revocation
│   │   └── envelope.py           # agent signature + linkage
│   ├── db/
│   │   ├── client.py             # asyncpg pool
│   │   └── queries.py
│   ├── aggregates.py             # aggregate helpers
│   ├── eligibility.py            # signed-predicate scope checks
│   └── config.py
└── tests/
    ├── test_verify_delegation.py
    ├── test_verify_envelope.py
    ├── test_predicate_derivation.py   # country→region, thresholds→age_band
    ├── test_uniqueness.py
    └── test_aggregate_recompute.py
```

---

## 6. `hearme-skill` — trust boundaries

```
┌─────────────────────────────────────────────────────────┐
│  hearme-broker (verified above; only contact in steady  │
│  state)                                                 │
└──────────────▲────────────────────┬─────────────────────┘
               │ envelope            │ open-questions poll
┌──────────────┴────────────────────▼─────────────────────┐
│  User device / server — Hermes Agent runtime            │
│  ┌──────────────────────────────────────────────────┐  │
│  │  hearme skill                                     │  │
│  │  - holds agent_key (Ed25519, on-disk encrypted)   │  │
│  │  - holds cached DelegationToken                   │  │
│  │  - never holds passport material                  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                 ▲
                 │ rare: install + refresh + revoke
                 │ (install = N quick Self proofs, §8.3)
┌────────────────┴───────────────────────────────────────┐
│  User phone — Self app                                  │
└────────────────────────────────────────────────────────┘
```

Three trust boundaries: broker, agent runtime, phone. The phone is touched only at the three enrollment moments. Steady-state traffic flows entirely between the agent and the broker.

---

## 7. `hearme-skill` — layered architecture

Eight layers. Linear flow, no per-question fork. Layers below never call layers above. The Relevance layer (§7.3) short-circuits the flow past Persona and Answerer when the user has no signal on the question — see §1.14.

```
        ┌────────────────────────┐
   in   │  Channel (broker I/O)  │   out
        └────────────┬───────────┘
                     │
        ┌────────────▼───────────┐
        │  Policy (gate)         │
        └────────────┬───────────┘
                     │
        ┌────────────▼───────────┐
        │  Relevance (cheap gate)│──┐
        └────────────┬───────────┘  │ below threshold:
                     │              │ skip Persona+Answerer,
                     │              │ emit no_signal envelope
        ┌────────────▼───────────┐  │
        │  Persona (projection)  │  │
        └────────────┬───────────┘  │
                     │              │
        ┌────────────▼───────────┐  │
        │  Answerer (LLM)        │  │
        └────────────┬───────────┘  │
                     │◄─────────────┘
        ┌────────────▼───────────┐
        │  Envelope              │
        │  reads cached          │
        │  DelegationToken,      │
        │  signs per-question    │
        └────────────┬───────────┘
                     │
        ┌────────────▼───────────┐
        │  Ledger (local SQLite) │
        └────────────┬───────────┘
                     │
        ┌────────────▼───────────┐
        │  UI (Hermes channels)  │
        └────────────────────────┘
```

The DelegationToken is set up out-of-band by `onboarding.py` (see §8) and lives encrypted on disk. Envelope reads it; nobody else does.

### 7.1 Channel — `broker.py`
- Polls the broker at `GET /v1/questions/open?since=<last_seen>` on a configurable interval (default 30s).
- Persists `last_seen` from broker-supplied `Question.created_at`, so local
  host clock skew cannot skip questions.
- Submits envelopes to `POST /v1/envelopes`.
- Backoff, retry, replay. No business logic.

### 7.2 Policy — `policy.py`
- Pure function `(question, user_policy, ledger_stats) -> Decision`.
- Decisions: `answer`, `decline`, `prompt_user`.
- User policy is plain YAML in `~/.hermes/hearme/policy.yaml`. Topics, askers, max/day, min payment, auto-submit window.
- Honeypot detection lives elsewhere; policy never branches on "is this a test".

### 7.3 Relevance — `relevance.py`

The cheap gate. Sits between Policy and Persona. Exists to satisfy §1.14: most users have no formed view on most questions, and we MUST detect that without spending a generation.

- Pure function `(question, memory_handle) -> RelevanceScore` where `RelevanceScore ∈ [0, 1]`.
- **Mechanics.** Embed the question (cheap, retrieval-tier model), run k-NN against the user's memory vector store through Hermes's memory abstraction (never importing a specific provider — §1.11), return a score derived from top-k similarity. No LLM generation, no chain-of-thought.
- **Cost asymmetry.** Retrieval-tier embedding lookup is ~100–1000× cheaper than a generation-tier LLM call. The whole point of this layer is to spend the retrieval cost so we don't spend the generation cost when the expected information yield is near zero.
- **Below threshold (`no_signal` branch).**
  - The flow short-circuits past Persona and Answerer.
  - Envelope (§7.6) emits `{answer: "", no_signal: true, relevance_score: <score>}` and signs it.
  - Cost of this branch is roughly one embedding call.
- **Above threshold.**
  - Flow continues to Persona (§7.4) and Answerer (§7.5).
  - The `relevance_score` is passed through and attached to the envelope as a confidence hint.
- **Threshold is question-stake-dependent.** Higher-staked questions justify a wider net (lower threshold) because the asker is implicitly paying for a broader sample; low-stake questions justify a tighter one. v0 ships a single global threshold and tunes from honeypot telemetry; per-stake tuning is v0.2 (§13).
- **Honeypot compatibility (§1.7).** Planted test questions are designed so an agent that actually runs *any* inference on the prompt — including the retrieval step — can detect the embedded instruction. The Relevance layer therefore does not let a lazy agent escape detection by emitting `no_signal` on tests. Test questions are calibrated to score above any reasonable threshold; an agent that emits `no_signal` on a planted test fails just as hard as one that fakes an opinion.
- **Privacy.** Retrieval and the gate decision happen entirely inside the user's runtime. The broker sees only the resulting envelope. Per-user `no_signal` patterns are linkable via `unique_identifier` — same tradeoff as §1.4 — and aggregation must surface only population-level no-signal rates, never per-user no-signal histories.
- **Calibration risk.** Threshold-too-high reproduces the self-selection bias Hearme is trying to escape (VISION.md Challenge #5: only the engaged answer). v0 starts gate-permissive and tightens via telemetry. The right endpoint is somewhere around 60–70% of dispatched questions reaching generation — wide enough to capture latent opinion, narrow enough to make the economics work.
- **Future optimization — opinion fingerprint.** Precompute, at install time and on a weekly refresh, a stable low-dimensional projection of the user's memory across topic axes. New questions match against the fingerprint with a single dot product. No memory scan per question. v0.2.

### 7.4 Persona — `persona.py`
- Pure function `(question, memory_handle) -> PersonaProjection`.
- Only runs when Relevance (§7.3) cleared the gate. If `no_signal`, Persona is skipped entirely.
- Queries Hermes memory through the provider interface; never imports a specific backend.
- Output is a **minimal sanitized snapshot** scoped to the question. No raw memory IDs, no source quotes, **no demographic fields** (those live in the DelegationToken).
- Must be deterministic-ish: same question + same memory state → same projection.

### 7.5 Answerer — `answerer.py`
- Single LLM call: `(persona_projection, question, style_guide) -> Answer`.
- Only runs when Relevance (§7.3) cleared the gate. The Answerer LLM call is the expensive part of the pipeline that the gate exists to protect.
- Returns an `Answer` plus a *local-only* rationale string for the audit trail. Rationale is never serialized into the envelope.
- Does **not** see the DelegationToken or `unique_identifier`. Strict separation between identity and inference.

### 7.6 Envelope — `envelope.py` + `delegation.py` + `crypto/`
- `delegation.py` loads the cached **broker-issued `DelegationToken`** (the session credential from `POST /v1/register`, §8.1) from encrypted storage. If expired, the layer fails the request and triggers a refresh prompt via the UI layer — re-registration re-runs the Self proofs; it does **not** silently call the phone in steady state.
- `envelope.py` builds:
  ```
  {
    question_id,
    answer,                   # "" when no_signal is true
    no_signal,                # bool, §7.3
    relevance_score,          # float in [0, 1], §7.3
    delegation_token,         # the broker-issued session credential (see §8)
    agent_signature,          # Sign(agent_key, H(question_id, answer, no_signal, relevance_score, nonce, delegation_hash))
    nonce                     # echo of the broker's per-question nonce
  }
  ```
- Both the `no_signal` and `relevance_score` paths produce envelopes with the same structure and the same signature scheme. A `no_signal` envelope is just an envelope with `answer = ""` and `no_signal = true`; the broker verifies it exactly the same way.

### 7.7 Ledger — `ledger.py`
- Local SQLite. Schema: `questions`, `answers`, `submissions`, `revocations`, `question_spend`.
- Primary key: `question_id`.
- Records `no_signal` and `relevance_score` for every submission so the user can audit which questions were skipped at the gate and why.
- Encrypted at rest.
- Read-only views to the UI layer.

### 7.8 UI — `ui.py`
- Uses Hermes's messaging-channel abstraction to prompt the user, send summaries, and **notify when the DelegationToken is about to expire** (7 days out).

---

## 8. Onboarding — the DelegationToken handoff

The only time the phone produces cryptographic material for the agent. Built on **Self** ([self.xyz](https://self.xyz)): passport/ID NFC + zk-SNARK, SNARK-verified **off-chain** on the self-bridge (`@selfxyz/core`'s `SelfBackendVerifier`), plus a one-time on-chain Celo Identity-Registry read at registration (§5). Per answer: no chain access.

### 8.0 Why a bridge sidecar (still)

`@selfxyz/core` (verify) and `@selfxyz/qrcode` / `SelfAppBuilder` (request creation) are Node-only; there is no pure-Python verifier. So the Python broker and skill delegate to **`packages/self-bridge`** over HTTP, exactly as the prior design did with zkPassport. The bridge does the cryptography; Python keeps every binding/structural check.

**Transport difference from zkPassport.** zkPassport relayed the finished proof back through its own request channel. Self instead has the **mobile app POST the proof directly to the `endpoint`** configured in the SelfApp — so the self-bridge *is* that endpoint (a callback webhook). The skill then polls the bridge for completion.

### 8.1 Flow

1. User installs the `hearme` Hermes skill. The skill generates an Ed25519 keypair → `agent_key`.
2. The skill asks the **self-bridge** `POST /requests {agentKey, profile}`. The bridge builds one or more SelfApp configs via `SelfAppBuilder` with:
   - `scope = "hearme-v1"` (≤31 ASCII; this *is* the nullifier scope),
   - `endpoint = <self-bridge callback URL>`, `endpointType = staging_https | https`,
   - `userId` = a per-request id, `userDefinedData = hex(agent_key)` (32-byte Ed25519 pubkey → 64 hex chars; **this is the agent-key bind** — the proof commits to it via `userContextData`),
   - disclosures per profile (§8.3): `nationality: true`, and a `minimumAge` threshold.
   It returns `{ requestId, urls: [...] }` (one universal-link/QR per threshold proof).
3. The skill renders each `url` as a QR in turn. User opens the **Self app**, taps their passport (a **mock passport** in staging — §12), approves. The Self app **POSTs the proof to the bridge `endpoint`**.
4. The bridge runs `SelfBackendVerifier.verify(...)` per submission, stores each `VerificationResult` under `requestId`. The skill polls `GET /requests/:id` until all expected proofs are `complete`, receiving for each: `nullifier` (= `unique_identifier`, identical across the threshold proofs since scope+passport are constant), disclosed `nationality`, the `olderThan` boolean, and `userDefinedData` (= `agent_key`).
5. The skill bundles the verified proofs into an **enrollment bundle** and `POST`s it to the broker `POST /v1/register` (it does **not** build the credential itself):
   ```
   EnrollmentBundle = {
     self_proofs,              # array; one verifiable bundle per threshold proof,
                               #   each = base64(canonical_json({attestationId, proof,
                               #                  publicSignals, userContextData}))
     agent_key,                # = userDefinedData inside every proof
   }
   ```
6. The broker runs the **registration pipeline** (§5): SNARK-verifies each proof via the self-bridge (must be within Self's ±1 day window — registration happens right after the scan, so this holds), enforces the bindings, re-derives `region`/`age_band`, atomically binds `nullifier ↔ agent_key` in the `registrations` registry, and returns the **broker-signed DelegationToken**:
   ```
   DelegationToken = {                # the session credential the agent replays per answer
     version = 2,
     scope = "hearme-v1",
     unique_identifier,        # Self nullifier (verified once, now authoritative)
     disclosed_predicates,     # bucketed by the broker: {age_band: "35-49", region: "EU"}
     agent_key,                # bound to unique_identifier in the registry
     issued_at,
     expires_at,               # default issued_at + 90 days (independent of Self's ±1 day proof window)
     broker_signature,         # Sign(broker_key, H(canonical_json(claims-without-signature)))
   }
   ```
   Integrity now comes from the **broker's signature** — its attestation that it verified the Self proofs once. The raw `self_proofs` are **not** stored in the token and never travel again.
7. Skill encrypts and stores the DelegationToken at `~/.hermes/hearme/delegation.token`; the raw `self_proofs` are discarded. Done.

**Graceful degradation.** Only the `18+` proof is required (registration gate). The finer thresholds (§8.3) are optional; a user who declines the extra scans gets `age_band = "18+"` and still participates — they just don't contribute to generational breakdowns.

### 8.2 Refresh
7 days before expiry, UI nudges the user. User opens the Self app, re-runs the proof set; the skill re-registers (`POST /v1/register`) and the broker re-verifies and re-issues the DelegationToken (same nullifier ⇒ idempotent registry bind). If ignored, the agent stops answering and surfaces a weekly nudge. (The Self ±1 day proof window is never a problem: registration always happens immediately after the scan.)

### 8.3 Disclosure profiles

Self discloses a *single* `minimumAge` boolean (or full DOB) per proof and the *raw* nationality — it has no native 5-year-band or "region" predicate. Hearme reconstructs both:

- **Region** ← disclosed `nationality` (ISO-3166 country), mapped to a region (`EU` / continent) and **bucketed by the broker at registration**. The raw country is in the proof, but the proof reaches the broker only once (at `/v1/register`); the broker stores only `region` and discards the raw country — it never re-travels per answer (§1.2).
- **Age band** ← a **multi-threshold ladder**: at install the skill requests several `older-than` proofs at thresholds `[18, 25, 35, 50, 65]` (configurable), all under `scope="hearme-v1"` so they share one nullifier. The set of passing thresholds reconstructs a band, e.g. `older_than(35)=T ∧ older_than(50)=F → "35-49"`. **Exact DOB is never disclosed.**

Profiles (picked once on the phone):
- **Minimal**: `{age_band: "18+", region: "EU/non-EU"}` — one proof.
- **Standard** (default): `{age_band: 5-band ladder, region: continent}` — full threshold set.
- *(Gender and finer geography are intentionally omitted in v0 to respect §1.2; add later only with a clear aggregation need and cohort-size suppression — §13.)*

### 8.4 Revocation
Phone publishes a signed revocation to the broker (`POST /v1/revocations` — out of v0 scope, but the broker has the `revocations` table ready). Broker stops accepting envelopes carrying the revoked `delegation_hash`.

### 8.5 Wire formats

**EnrollmentBundle** (what `POST /v1/register` accepts — install only, never stored):
```json
{
  "self_proofs": [
    "<base64 of canonical_json({attestationId, proof, publicSignals, userContextData})>"
  ],
  "agent_key": "<base64 32 bytes>"
}
```

**DelegationToken** (the broker-issued session credential `POST /v1/register` returns; canonical JSON, deterministic field ordering for hashing):
```json
{
  "version": 2,
  "scope": "hearme-v1",
  "unique_identifier": "<Self nullifier string>",
  "disclosed_predicates": {"age_band": "35-49", "region": "EU"},
  "agent_key": "<base64 32 bytes>",
  "issued_at": "2026-05-19T10:00:00Z",
  "expires_at": "2026-08-17T10:00:00Z",
  "broker_signature": "<base64 64 bytes>"
}
```

`broker_signature = Sign(broker_key, H(canonical_json(token-without-broker_signature)))`. The agent treats the token as opaque; only the broker can mint or validate it.

**Envelope** (what `POST /v1/envelopes` accepts):
```json
{
  "question_id": "<uuid>",
  "answer": "Plain text answer from the agent.",
  "nonce": "<base64 from the question record>",
  "delegation_token": { /* DelegationToken */ },
  "agent_signature": "<base64 64 bytes>"
}
```

`agent_signature = Sign(agent_key, H(question_id || answer || nonce || delegation_hash))`
`delegation_hash = SHA-256(canonical_json(delegation_token))`

---

## 9. Monorepo layout

```
hearme/
├── README.md
├── ARCHITECTURE.md
├── docker-compose.yml             # postgres + broker + web + self-bridge for local dev
├── packages/
│   ├── web/                       # § 4 — Next.js
│   ├── broker/                    # § 5 — Python/FastAPI
│   ├── skill/                     # § 6-8 — Python Hermes skill
│   ├── self-bridge/               # Node sidecar — real Self request + verify (@selfxyz/core)
│   └── proto/                     # shared schemas
│       ├── enrollment.json        # EnrollmentBundle (POST /v1/register input)
│       ├── self.json              # verifiable Self proof bundle (inside EnrollmentBundle)
│       ├── delegation.json        # broker-issued DelegationToken (session credential)
│       ├── envelope.json
│       └── question.json
└── scripts/
    ├── dev-up.sh                  # docker-compose up + seed
    └── mock-onboard.py            # replays a captured proof fixture through /v1/register into a token
```

`packages/proto/` holds the canonical JSON schemas. Both `broker` and `skill` validate against them; `web` doesn't need them (it doesn't touch envelopes).

---

## 10. End-to-end lifecycle of one question

```
asker browser → /ask form → server action → INSERT into questions
                                                   │
                                                   ▼
                                              Postgres (status='open')
                                                   │
                                                   │ broker has no push;
                                                   │ agents poll
                                                   ▼
                                          GET /v1/questions/open?since=…
                                                   │
                                                   ▼
                                              Hermes skill receives Question
                                                   │
                                          ┌────────┴────────┐
                                          │ Policy: gate    │
                                          │ Persona: project│
                                          │ Answerer: LLM   │
                                          │ Envelope: sign  │
                                          └────────┬────────┘
                                                   │
                                                   ▼
                                          POST /v1/envelopes
                                                   │
                                                   ▼
                                          broker.verify pipeline
                                                   │
                                                   ▼
                                          INSERT envelopes (UNIQUE check)
                                          + UPDATE aggregates
                                                   │
                                                   ▼
                                          Postgres
                                                   │
                                                   │ frontend revalidates
                                                   ▼
                                          /q/[id] reflects new answer
```

No phone contact anywhere in this lifecycle. The phone was only needed at install and at refresh.

---

## 11. What v0 skips

Marked `# STUB:` in code and listed in each package's README under "Not yet real":

- **Payments.** No money flows anywhere in v0. The pitch's "fraction of a cent" is deferred to v0.3. No payment fields in the schema.
- **Asker auth.** Display name only; anyone can post. Asker accounts and auth land in v0.2.
- **Real Self proof verification, verify-once — DESIGN (this change).** At `POST /v1/register`, `verify/self_identity.py` runs `@selfxyz/core`'s `SelfBackendVerifier.verify()` through the **self-bridge** (`packages/self-bridge`, a Node sidecar — `@selfxyz/core` is Node-only) on the enrollment bundle, enforces the bindings (agent_key via `userDefinedData`, scope, one shared nullifier ↔ unique_identifier), **derives** `region`/`age_band` from the disclosed nationality and older-than booleans, atomically binds the nullifier ↔ agent_key in the `registrations` registry, and `verify/credential.py` issues a **broker-signed DelegationToken**. Per envelope, only that token's broker signature + registry/revocation are checked — **no Self proof at answer time** (forced by Self's ±1 day proof window; also removes per-envelope SNARK cost and closes the §1.2 transit gap). Mock-passport proofs verify only with `SELF_MOCK_PASSPORT=1` (staging / Celo Sepolia). See `packages/proto/{enrollment,self,delegation}.json` and `packages/broker/src/hearme_broker/verify/`. *Flips to DONE once the code lands; migration plan is `SELF_MIGRATION.md`.* **Sybil hardening:** at registration the broker also performs a one-time on-chain read of Self's Celo Identity Registry to confirm the proof's Merkle root is live (§5) — this anchors the off-chain SNARK to the real registry (where one-passport→one-identity is enforced) and is the only on-chain dependency. **Residual caveats:** (a) a *Celo-side revocation made after registration* is not re-checked per answer (Hearme's own `registrations` registry governs revocation thereafter); (b) one human holding multiple legal passports yields multiple nullifiers — see the Sybil-resistance discussion in `IDENTITY.md`.
- **Memory provider abstraction.** Skill hard-codes one provider (Mem0 or Holographic). Wire the abstraction in v0.2.
- **Multi-channel skill UI.** Telegram only in v0.
- **Revocation propagation.** Broker has the `revocations` table; skill respects expiry; live revocation publishing flow lands in v0.2.
- **Honeypot signal handling.** Stubbed; broker feedback parsing in v0.2.
- **Real-time frontend.** Frontend polls every 10s on the detail page. WebSocket/SSE in v0.2.
- **Lost-phone recovery.** Re-enroll from a fresh install.

**No silent stubs.** Anything stubbed appears in code with `# STUB:` and in the README.

---

## 12. Testing posture

Each package has its own test suite; one cross-cutting end-to-end suite at the repo root.

### web
- Server action `createQuestion` — happy path + validation.
- Detail page renders aggregate results without exposing raw envelopes.

### broker — the highest-stakes suite
- **Registration (`/v1/register`)** — happy path issues a broker-signed token; ZK failures (proof-invalid, expired-proof/`InvalidTimestamp`, binding mismatch on agent_key/scope, proofs with differing nullifiers) rejected; **Sybil bind** — a second registration of the same nullifier with a *different* agent_key rejected, same agent_key re-issues. The bridge call is mocked in unit tests (a deterministic fake returning a canned `VerificationResult`); a live `SELF_MOCK_PASSPORT=1` (staging) verify is opt-in.
- **Predicate derivation** — `country → region` mapping and `older-than-booleans → age_band` bucketing are pure functions: table-driven tests over edge cases (boundary ages, unmapped countries, partial threshold sets → graceful `18+`). The broker, not the client, is authoritative.
- **Credential (`credential.py`)** — round-trip sign/verify; tampered claim (swapped predicate / agent_key / unique_identifier / expiry) fails the broker signature; a token signed by a non-broker key is rejected.
- **Verify envelope** — happy path, expired token, revoked/unknown registration, bad agent signature, swapped `question_id`, swapped `answer`, swapped `nonce`, swapped `delegation_hash`. Each must reject. **No bridge call** on this path (assert the bridge client is never invoked).
- **Uniqueness** — two envelopes from the same `unique_identifier` for the same `question_id` → second rejects via DB constraint. (Test against a real Postgres in CI.)
- **Aggregate increment** — accepted envelopes update `total_answers` and `by_predicate` without scanning all prior envelopes.

### skill
- **Policy and ledger** — pure / deterministic unit tests.
- **Delegation lifecycle** — fresh load, expiry behavior, signature verification, refresh.
- **Envelope signing** — property tests asserting `agent_signature` binds correctly; rejects on any swap.
- **Persona projection** — snapshot tests against synthetic memory.
- **Answerer** — vcr-style recorded LLM responses; never live LLM in CI.
- **Identity-inference separation** — `Answerer` test double asserts on its call args; must never see DelegationToken or `unique_identifier`.
- **No phone contact in steady state** — across 100 simulated answers, phone bridge is called **zero** times.

### end-to-end (`/scripts/e2e.sh`)
- Spin up postgres + broker + web + self-bridge + a skill. Onboard by scanning a mock passport (`SELF_MOCK_PASSPORT=1`, staging) or replaying a captured proof fixture via `mock-onboard.py` → `POST /v1/register` → broker-issued token; assert a `registrations` row appears.
- Asker posts a question via the web UI (programmatically).
- Mock skill polls broker, answers, submits envelope.
- Assert: envelope appears in DB, aggregate row updated, web detail page renders it.
- **No-bridge-at-answer-time assertion:** the self-bridge is hit during `/v1/register` but **zero** times during `/v1/envelopes`.
- **Boundary-leakage assertion:** scrape the POST body to `/v1/envelopes`; assert it contains exactly `{question_id, answer, no_signal, relevance_score, nonce, delegation_token, agent_signature}` and that `delegation_token` carries **no** `self_proofs`. No raw proof leaves the device per answer.

---

## 13. Open questions

- **Question dispatch transport.** v0 uses HTTP polling. Latency vs simplicity tradeoff: polling every 30s means answers arrive ~30s late. Worth it for v0; move to SSE or WebSocket in v0.2.
- **Epoch-rotated scopes (privacy upgrade).** Replace `scope="hearme-v1"` with `scope="hearme-epoch-<N>"` where N rotates monthly (still ≤31 ASCII). Phone issues a small batch of epoch tokens at install. Benefit: broker can no longer link a user's answers across epochs. Note Self derives the nullifier from `scope`, so a new scope yields a fresh nullifier for the same passport.
- **Broker signing-key management.** The broker-issued DelegationToken is only as trustworthy as the `broker_key`. Where does it live (KMS / HSM / env), and how is it rotated? A rotation needs an overlap window where the broker accepts tokens from the previous key (or forces re-registration). v0: single key in config; harden in v0.2.
- **Credential-vs-registry revocation latency.** Revocation flips `registrations.revoked_at`, checked per envelope — so revocation is immediate, but a stolen token works until then (and short of revocation, until `expires_at`). Shortening the credential TTL trades refresh friction for a tighter compromise window.
- **DelegationToken storage at rest.** OS keychain, passphrase-encrypted file, or Hermes-identity-derived key? Tradeoff between usability and host-compromise resistance.
- **Aggregate semantics for free-form answers.** v0 only aggregates by predicate (e.g., "47 EU users answered"). Semantic clustering of answer text — "65% positive sentiment about X" — is v0.2 and needs careful design to not leak identifying patterns.
- **Frontend identity for askers.** v0 has no auth. At what scale does this become a problem (spam, abuse)? Likely sooner than we'd like.
- **What happens if the agent host is compromised mid-session.** Attacker has agent_key + the broker-issued DelegationToken; can submit answers until the registration is revoked (`registrations.revoked_at`) or the token expires. Broker rate-limit per `unique_identifier` is the v0 bound.
- **Memory provider query richness.** Does Hermes's abstraction expose enough for topic-scoped retrieval, or do we need our own layer?
- **Auto-submit window default.** 0 (always prompt) or non-zero (trust the policy)? Shapes user expectations forever.
