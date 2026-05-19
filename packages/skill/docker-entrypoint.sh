#!/bin/sh
# Skill container bootstrap. Idempotent.
#
# 1. Ensures the root dir exists.
# 2. Generates the agent key if missing (load_or_create_agent_keypair).
# 3. Mints a dev DelegationToken via scripts/mock-phone.py if none on disk.
# 4. Writes a permissive dev policy.yaml if none is mounted.
# 5. Execs the dev runner, which provides a stub host (FakeLLM, auto-approve
#    channel, Mem0 stub memory) and starts the broker-polling loop.
#
# All of this is dev-only. Real Hermes integration replaces this entrypoint
# with the Hermes runtime, which provides the host instead.
set -eu

ROOT="${HEARME_SKILL_ROOT_DIR:-/data}"
mkdir -p "$ROOT"

# --- Step 2: load-or-create agent key. ------------------------------------
# Reuse the skill's keystore so we get the exact same on-disk format.
AGENT_PUB_B64="$(python - <<'PY'
import base64, os
from pathlib import Path
from hearme_skill.crypto.keystore import load_or_create_agent_keypair
path = Path(os.environ.get("HEARME_SKILL_ROOT_DIR", "/data")) / "agent_key"
kp = load_or_create_agent_keypair(path)
print(base64.b64encode(kp.public_bytes).decode("ascii"))
PY
)"
echo "[hearme-skill] agent pubkey = $AGENT_PUB_B64"

# --- Step 3: mint DelegationToken if not present. -------------------------
if [ ! -f "$ROOT/delegation.token" ]; then
  echo "[hearme-skill] minting dev DelegationToken via mock-phone..."
  python /usr/local/bin/mock-phone.py mint \
    --agent-pubkey-b64 "$AGENT_PUB_B64" \
    --unique-id "${HEARME_SKILL_UNIQUE_ID:-dev-user-1}" \
    --profile "${HEARME_SKILL_PROFILE:-standard}" \
    --ttl-days 90 \
    > "$ROOT/delegation.token.tmp"
  mv "$ROOT/delegation.token.tmp" "$ROOT/delegation.token"
  chmod 600 "$ROOT/delegation.token"
fi

# --- Step 4: default dev policy. ------------------------------------------
if [ ! -f "$ROOT/policy.yaml" ]; then
  cat > "$ROOT/policy.yaml" <<EOF
# Dev policy. The skill container auto-approves answers so the e2e flow
# runs without a human in the loop. Production users author this file by
# hand (ARCHITECTURE.md §7.2).
auto_answer: true
auto_submit_window_seconds: 5
max_answers_per_day: 50
EOF
fi

# --- Step 5: hand off to the dev runner. ----------------------------------
exec python -m hearme_skill.dev_runner
