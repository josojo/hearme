# hearme-skill

The Hearme Hermes skill — a local agent that answers questions on the user's
behalf, signs them, and submits them to the broker.

See [ARCHITECTURE.md §6-8](../../ARCHITECTURE.md) for the canonical spec this
package implements. This README documents how to install, run, and test it.

## Architecture overview

Seven linear layers (ARCHITECTURE.md §7). Each layer is one module; layers
below never call layers above.

```
        ┌────────────────────────┐
   in   │  Channel (broker I/O)  │   out          broker.py
        └────────────┬───────────┘
                     │
        ┌────────────▼───────────┐
        │  Policy (gate)         │                policy.py
        └────────────┬───────────┘
                     │
        ┌────────────▼───────────┐
        │  Persona (projection)  │                persona.py + memory/
        └────────────┬───────────┘
                     │
        ┌────────────▼───────────┐
        │  Answerer (LLM)        │                answerer.py + llm/
        └────────────┬───────────┘
                     │
        ┌────────────▼───────────┐
        │  Envelope              │                envelope.py + delegation.py
        │  (signs, binds nonce)  │                + crypto/
        └────────────┬───────────┘
                     │
        ┌────────────▼───────────┐
        │  Ledger (local SQLite) │                ledger.py
        └────────────┬───────────┘
                     │
        ┌────────────▼───────────┐
        │  UI (Hermes channels)  │                ui.py
        └────────────────────────┘
```

The DelegationToken is set up out-of-band by `onboarding.py` (§8) and lives
encrypted on disk. **The Envelope layer is the only layer that reads it.**
In particular, **the Answerer never sees the DelegationToken or
`unique_identifier`** — enforced by the function signature in `answerer.py`
and asserted by `tests/test_identity_inference_separation.py`.

## Install + run

```bash
# from packages/skill/
pip install -e '.[dev]'

# 1. Generate the agent key + show the QR for ZKPassport
hearme-skill onboard --node-id hermes-local-0

# 2. (Dev only) Accept a mock delegation token instead of a real phone:
python ../../scripts/mock-phone.py > /tmp/token.json
hearme-skill accept-mock-delegation /tmp/token.json

# 3. Configure policy (sample below). Hearme defaults to off.
$EDITOR ~/.hermes/hearme/policy.yaml
```

In production, Hermes loads the skill via the entry point
`hermes.skills = hearme_skill.skill:entrypoint`. Hermes passes a `host`
object exposing `.memory`, `.llm`, `.channel`, and `.node_id`. The skill
adapts each to the protocols in `memory/provider.py`, `llm/client.py`, and
`ui.py`. **Real Hermes integration is wired via a config block in the host
process** — see the Hermes runtime docs; this package only defines the
adapter side.

## Sample `policy.yaml`

```yaml
# ~/.hermes/hearme/policy.yaml
#
# All categories default to off (§1.1). The skill will *prompt* the user
# even after a policy match unless `auto_answer: true` is set, and even
# then `auto_submit_window_seconds: 0` means we still preview every answer
# before submission (§1.12 override is sacred).

topic_allowlist:
  - coffee
  - travel
topic_blocklist:
  - politics

max_answers_per_day: 50
min_payment: 0.0              # v0: ignored, no payment field on questions
auto_submit_window_seconds: 0 # 0 = always prompt; non-zero = veto window
auto_answer: false
```

## Configuration knobs (env vars, prefix `HEARME_SKILL_`)

| Variable                                | Default                  | Meaning                                              |
|-----------------------------------------|--------------------------|------------------------------------------------------|
| `HEARME_SKILL_BROKER_URL`               | `http://localhost:8000`  | Where to find `hearme-broker`.                       |
| `HEARME_SKILL_POLL_INTERVAL_SECONDS`    | `30`                     | Cadence for `GET /v1/questions/open`.               |
| `HEARME_SKILL_AUTO_SUBMIT_WINDOW_SECONDS` | `0`                    | Default preview window (policy.yaml overrides).      |
| `HEARME_SKILL_ROOT_DIR`                 | `~/.hermes/hearme/`      | Where keys, ledger, and token live.                  |

The polling cursor is stored locally in the ledger from the max
broker-supplied `Question.created_at` value seen in a response. It does not
advance from the agent host's wall clock.

## Privacy guarantees

What the broker sees, per envelope (the five-field POST body in §8.5):
`question_id`, `answer`, `nonce`, `delegation_token`, `agent_signature`.

What the broker NEVER sees:
- The user's raw memory / source quotes / chain-of-thought.
- The `Answer.rationale` field (it never leaves the local ledger).
- Demographic fields outside what's pre-baked into the DelegationToken's
  `disclosed_predicates` at install time (§1.3).
- Passport material (the skill never holds it; the phone does).
- Whether a question is a honeypot (the skill doesn't even ask itself —
  §1.7).

Coercion resistance (§1.6): the skill emits no signed receipt beyond the
envelope itself, ships no plaintext log off-device, and takes no
screenshots. The local audit trail in `~/.hermes/hearme/ledger.sqlite` is
the only persistence.

## Testing

```bash
pytest
```

Mandatory tests (per ARCHITECTURE.md §12, all in `tests/`):

- `test_policy.py` — deterministic gate decisions.
- `test_ledger.py` — schema + idempotency.
- `test_delegation_lifecycle.py` — load / expiry / refresh-window detection.
- `test_envelope_signing.py` — property: flip any byte → signature rejects.
- `test_persona_projection.py` — snapshot tests; no demographics or raw IDs.
- `test_answerer.py` — fake LLM client, no live calls.
- `test_identity_inference_separation.py` — answerer double asserts on call
  args; can never receive DelegationToken / `unique_identifier`.
- `test_no_phone_contact.py` — 100 simulated answers, phone bridge mock
  receives ZERO calls (§1.13).

Per §12, **no live LLM calls in CI**. All Answerer tests use the
deterministic `FakeLLMClient` in `llm/client.py`.

## Not yet real (every `# STUB:` in code)

- **Payments.** No payment fields on the wire; `policy.min_payment`
  parsed for forward-compat but never read. (ARCHITECTURE.md §11)
- **Memory provider.** One hardcoded `Mem0StubProvider` returning
  synthetic, sanitized facts. Real memory abstraction lands in v0.2.
- **Multi-channel UI.** Telegram-only in v0; `InMemoryChannel` stub for
  tests. The `Channel` Protocol is the v0.2 plug point.
- **Live revocation handling.** The skill respects expiry; it does not yet
  consult a broker-side revocation feed. The broker already has the
  `revocations` table ready.
- **Honeypot signal parsing.** Stubbed; the Policy layer deliberately
  never branches on "is this a test" (§1.7).
- **Encrypted-at-rest storage.** Both the agent key (`crypto/keystore.py`)
  and the delegation token (`delegation.py`) are written as plaintext with
  0600 perms. SQLCipher / OS keychain in v0.1. Ledger encryption likewise.
- **Real zkPassport circuit verification.** v0 trusts the phone's Ed25519
  signature on the bundle; circuit verification is broker-side and lands in
  v0.2.
- **Lost-phone recovery.** Re-enroll from a fresh install.

## Design choices worth flagging

- **Default `auto_submit_window_seconds = 0`** (prompt-always). §1.12
  "override is sacred" and §13's open question about the right default —
  v0 errs maximally on the side of user control. Users can opt into a
  non-zero veto window per-deployment via `policy.yaml`.
- **`Answer.rationale` is captured locally** for the audit ledger, but the
  `build_envelope` API takes `answer_text: str` (not `Answer`) so it's
  structurally impossible for the rationale to slip onto the wire.
- **Persona projection is paranoid about demographics**: even though the
  v0 memory stub never emits demographic fields, `persona.project` filters
  any fact whose lowercased form starts with `age:`, `gender:`, `country:`,
  `region:`, or `ethnicity:`. Demographics live in the DelegationToken
  only.

## Wire-format alignment

The Pydantic models in `hearme_skill.models` mirror `packages/proto/`
field-for-field. The canonical-JSON helper in `hearme_skill.crypto.canonical`
produces byte-identical output to the broker's verifier (sorted keys, no
whitespace, UTC `Z` suffix). The end-to-end suite at the repo root will
fail if these drift apart.
