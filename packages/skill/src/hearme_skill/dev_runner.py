"""Dev runner — boots the skill loop with stub host adapters.

Used by docker-compose so `docker compose up` produces a working end-to-end
flow without a Hermes runtime in the loop. Provides:

* ``FakeLLMClient`` so no network LLM call happens (per §12 — never live
  LLM in CI/dev defaults).
* An auto-approve channel so the preview/confirm step doesn't block on
  user input.
* ``Mem0StubProvider`` as the memory backend.

Real Hermes integration replaces this with whatever the Hermes runtime
hands to ``skill.entrypoint(host)``.
"""

from __future__ import annotations

import asyncio
import logging
import os

from .llm.client import FakeLLMClient
from .memory.mem0_stub import Mem0StubProvider
from .skill import run_loop
from .ui import InMemoryChannel


class _AutoApproveChannel(InMemoryChannel):
    """Auto-replies 'ok' to every prompt — dev only.

    A real channel surfaces the prompt to the user (Telegram, browser push,
    etc.); this stub stands in so the loop doesn't block waiting for input.
    """

    async def prompt(self, message: str, *, timeout_seconds: float | None = None) -> str | None:
        self.sent.append(message)
        return "ok"


class _DevHost:
    """Minimal host shape the skill's ``run_loop`` expects (see skill.py)."""

    def __init__(self) -> None:
        self.llm = FakeLLMClient()
        self.memory = Mem0StubProvider()
        self.channel = _AutoApproveChannel()
        self.node_id = os.environ.get("HEARME_SKILL_NODE_ID", "dev-host-0")


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("HEARME_SKILL_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_loop(_DevHost()))


if __name__ == "__main__":
    main()
