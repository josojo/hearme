# Hearme Identity Model — zkPassport and Self.xyz

> Identity is the foundation of Hearme. Without a credible "one human, one voice" guarantee, every aggregate signal the platform produces is worthless.

## The Problem

Hearme's political signal is only meaningful if each verified human counts once. Two failure modes are equally fatal:

1. **Sybil attacks** — a single actor (a bot farm, a state, a coordinated campaign) creates many identities and inflates a position they want amplified.
2. **Double counting** — a single honest user accidentally votes twice because the system treats different credentials (X, WorldCoin, email) as parallel voting rights.

Both fail for the same reason: if the *credential* is what grants a vote, anyone with multiple credentials gets multiple votes, and there is no way to deduplicate without linking identities (which destroys anonymity).

The fix is architectural: **the vote belongs to a Hearme identity, and a Hearme identity can only be created by presenting a unique-personhood proof at registration.** Other credentials (X, GitHub, ENS) can be attached later as reputation metadata, but they never create a new voting identity.

This document describes how **zkPassport** and **Self.xyz** are used as the unique-personhood proofs that gate Hearme account creation.


---

## Why Passport-Based Proof of Personhood

Modern biometric passports (ICAO 9303) contain an NFC chip with personal data signed by the issuing country's signing authority. The signature chain anchors to the country's Country Signing Certificate Authority (CSCA), whose public keys are published in the ICAO Public Key Directory.

This gives us, for free, a globally distributed proof-of-personhood infrastructure:

- ~1.4 billion biometric passports in circulation
- Issued by ~190 governments
- Cryptographically signed, tamper-evident
- Each passport is, by issuing-state policy, tied to one human

Combining this with zero-knowledge proofs lets a user prove "I hold a valid passport from country X, I am over 18, and here is a Hearme-scoped nullifier" — **without revealing the passport itself, the document number, or their name.**

Compared to the alternatives:

| Mechanism            | Coverage         | Privacy       | Vendor risk        | Regulatory risk            |
|----------------------|------------------|---------------|--------------------|----------------------------|
| WorldCoin (iris)     | Growing, gated   | Strong (ZK)   | Single vendor      | Banned/restricted in many countries |
| Humanity Protocol    | Early            | Strong        | Single vendor      | Unproven                   |
| Government KYC       | Universal-ish    | None          | KYC provider       | High (data leakage)        |
| Social vouching      | Limited          | Medium        | Distributed        | Vulnerable to coordinated attacks |
| **Passport + ZK**    | **~1.4B users**  | **Strong**    | **Open standard**  | **Low**                    |

Passport-based ZK is the strongest currently-deployable option for global coverage with reasonable privacy.


---

## zkPassport

zkPassport is an open-source SDK and mobile app that lets a user scan their passport's NFC chip with their phone and generate zero-knowledge proofs about its contents.

**What it proves:**
- The passport is signed by a real CSCA listed in the ICAO directory.
- The passport has not expired.
- Selectively disclosed attributes: nationality, age bracket, etc. — the user chooses what to reveal.
- A **scope-bound nullifier**: a deterministic value derived from the passport identity *and* the verifying application's scope (e.g., `"hearme"`), used to prevent the same passport from registering twice in the same app.

**What it does not reveal:**
- The passport number.
- The holder's name.
- The holder's exact date of birth (unless they choose to disclose it).
- The holder's photo.

**How Hearme uses it:**

1. User opens Hearme registration, chooses "verify with passport (zkPassport)."
2. Hearme presents a QR code containing the Hearme app scope and the requested disclosures (e.g., country, age ≥ 16).
3. User scans the QR code with the zkPassport mobile app, taps their passport to their phone's NFC reader.
4. The zkPassport app generates a proof locally on the device.
5. The proof is submitted to Hearme's verifier. Hearme checks:
   - The proof is valid against the ICAO root keys.
   - The scope matches `"hearme"`.
   - The nullifier has not been seen before in Hearme's nullifier registry.
6. If valid and unique, a Hearme identity is created, bound to the nullifier. The disclosed attributes (country, age bracket) are stored as the identity's demographic metadata.

The nullifier is the load-bearing piece. Because it is deterministic in `(passport, scope)`, the same passport scanned twice produces the same nullifier — and Hearme rejects the second registration.


---

## Self.xyz

Self.xyz (Self Protocol) is a similar passport-based identity system developed in the Celo ecosystem. It uses the same underlying technology — passport NFC + zk-SNARKs — and provides analogous guarantees, with a few different design choices.

**What it offers:**
- Passport NFC scanning via a self-custodial mobile app.
- ZK proofs of nationality, age, and OFAC sanctions-list non-membership.
- Per-app nullifiers for Sybil resistance.
- Smart-contract verifiers on Celo, with cross-chain support planned/available.
- A free tier suitable for permissionless apps.

**How Hearme uses it:**

The flow mirrors zkPassport:

1. User chooses "verify with passport (Self)."
2. Hearme presents a Self verification request with the Hearme scope and the attributes to disclose.
3. User completes the flow in the Self app.
4. Hearme verifies the proof on-chain or via the Self SDK, checks the nullifier against its registry, and creates the identity.

**Why offer both:**
- Different passports may be better supported by one SDK than the other (chip variants, CSCA coverage, regional differences).
- Different user-experience preferences.
- Resilience: if one system has downtime or a vulnerability, the other remains available.
- Avoiding a single-vendor dependency, which is itself a legitimacy risk for a global platform.


---

## The Cross-System Deduplication Problem

Offering both zkPassport and Self.xyz creates a subtle attack surface: **the same passport, used in both systems, will produce two different nullifiers** (because each system derives nullifiers using its own scheme). A motivated user could register one Hearme identity via zkPassport and a second via Self.xyz, with the same physical passport.

This is a real concern. Options to mitigate:

**Option A — Shared nullifier derivation.**
Both systems publish a nullifier derived from a canonical passport identifier (e.g., `hash(DG1 || "hearme")`, where DG1 is the standardized machine-readable zone of the passport). If both SDKs cooperate on this scheme, the same passport produces the *same* Hearme nullifier through either path, and Hearme's nullifier registry deduplicates across systems.

This is the right long-term answer. It requires coordination with both projects, but the cryptographic primitives already exist — both already extract DG1 internally. Hearme's onboarding milestone should include reaching out to both teams to standardize a common Hearme-scoped nullifier derivation.

**Option B — Single-system enforcement.**
Designate one of the two as canonical for any given passport-country pair. For example: passports from countries with strong Self.xyz coverage default to Self; everything else falls back to zkPassport. Users do not get to pick.

Reduces flexibility, but eliminates the duplication path entirely.

**Option C — Accept the marginal duplication risk.**
A user who wants to double-vote must (a) own a valid passport, (b) install and complete *both* mobile flows, (c) accept that each flow links a Hearme identity to a specific demographic disclosure. The economic and friction cost of doing this for one extra vote is high. For small-stake questions, this is tolerable; for high-stake political signals, it is not.

**Recommended starting point:** ship with Option B (single system per passport country, with a documented fallback path), and pursue Option A as a roadmap item once both SDKs and Hearme are in production.


---

## What the Hearme Identity Looks Like After Registration

After successful passport verification, a Hearme identity consists of:

- **Nullifier** — the unique, scope-bound identifier. Used to prevent re-registration. Never displayed.
- **Demographic disclosures** — country of issuance, age bracket. Used for the regional/demographic breakdowns shown on aggregate results. Disclosed only at the granularity the user chose during registration.
- **Reputation stamps** (optional, attached later) — X account, GitHub, ENS, Lens, prior Hearme participation. These never create new voting rights; they only feed a reputation score that may be displayed alongside aggregates or used for weighted sampling.
- **Agent binding** — the user's personal AI agent, authorized to answer on their behalf. Revocable.
- **Public key** — for signing votes and receiving payouts. The key is generated locally, never linked back to the passport.


---

## Limitations and Honest Caveats

1. **Not everyone has a biometric passport.** Coverage skews toward wealthier and more travel-active populations. Hearme's demographic breakdowns will reflect this skew until additional unique-personhood proofs (Aadhaar via Anon Aadhaar, national ID schemes, social-graph systems for the unbanked) are added.

2. **Passport sharing and coercion.** A passport can be physically borrowed, surrendered, or seized. ZK proofs cannot prevent a coerced user from scanning their own passport on someone else's behalf. MACI-style collusion resistance addresses *vote-time* coercion but not *registration-time* coercion. This is an open problem.

3. **Stolen passports.** A stolen passport with a known PIN-equivalent can register a Hearme identity for someone other than the rightful holder. The rate is low but nonzero; reporting and revocation mechanisms are needed.

4. **State-level attacks.** A government with control over its CSCA could issue fake passports and create fake Hearme identities at scale. Mitigations: monitor per-country registration rates, flag anomalies, optionally weight or cap per-country participation in any single question.

5. **Cross-system duplication.** As discussed above. Mitigated by shared nullifier derivation in the long term.

6. **Privacy of demographic disclosures.** Even age bracket + country can be deanonymizing in small populations. For low-population countries or rare demographic intersections, Hearme should aggregate or suppress breakdowns below a minimum cohort size.


---

## Open Questions

- Should Hearme require the same passport-scoped nullifier to be used across re-registrations (e.g., if a user loses their device), or accept a new nullifier from the same passport? The former is more Sybil-resistant; the latter is more user-friendly.
- How should expired-passport users be handled? Re-verify with the renewed passport? Allow a grace period?
- What is the right cohort-size threshold below which demographic breakdowns are suppressed?
- How are passport-less populations (~30% of humanity) brought in without weakening the Sybil guarantee for the rest?

These are questions for the next iteration of this document, not blockers for the initial design.
