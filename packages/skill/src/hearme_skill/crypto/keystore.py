"""Agent-key on-disk storage.

# STUB: v0 writes the 32-byte Ed25519 seed to disk with 0600 permissions but
# does NOT encrypt it (no passphrase prompt, no OS keychain integration).
# v0.1 should derive a wrapping key from a user passphrase or the Hermes
# identity key (see ARCHITECTURE.md §13 "DelegationToken storage at rest"
# — the same tradeoff applies to the agent key). Anyone with read access to
# the user's home directory can currently impersonate the agent.
"""

from __future__ import annotations

import os
from pathlib import Path

from .ed25519 import Keypair, generate_keypair, keypair_from_seed


def store_agent_keypair(path: Path, keypair: Keypair) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file then rename so we never leave a half-written key.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(keypair.private_bytes)
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def load_agent_keypair(path: Path) -> Keypair:
    seed = path.read_bytes()
    if len(seed) != 32:
        raise ValueError(f"Agent key at {path} is {len(seed)} bytes; expected 32.")
    return keypair_from_seed(seed)


def load_or_create_agent_keypair(path: Path) -> Keypair:
    if path.exists():
        return load_agent_keypair(path)
    kp = generate_keypair()
    store_agent_keypair(path, kp)
    return kp
