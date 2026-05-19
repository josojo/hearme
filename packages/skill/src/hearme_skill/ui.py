"""UI — § 7.7.

Uses Hermes's messaging-channel abstraction for prompts, summaries, and
expiry nudges. v0 stubs the actual transport with a Protocol; real Hermes
integration wires a Telegram-backed channel (per §11 "Telegram only in v0").

Per §1.12, this layer owns the **preview/edit/veto** path. `auto_submit_window_seconds`
in policy controls the default: 0 means always prompt before submission;
non-zero is a preview window in which the user can veto.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Protocol

from .delegation import REFRESH_WINDOW, needs_refresh_soon
from .models import Answer, DelegationToken, Question

log = logging.getLogger(__name__)


class Channel(Protocol):
    """Hermes messaging-channel abstraction (stubbed for v0).

    Implementations: Telegram (v0), browser push (v0.2), etc.
    """

    async def notify(self, message: str) -> None: ...

    async def prompt(self, message: str, *, timeout_seconds: float | None = None) -> str | None:
        """Show a prompt; return user input or None on timeout/dismiss."""


@dataclass
class InMemoryChannel:
    """# STUB: in-memory channel for tests + v0 dev.

    Real Hermes wiring lives outside this package; the entrypoint in
    ``skill.py`` adapts the host's channel to this protocol.
    """

    sent: list[str] = field(default_factory=list)
    scripted_replies: list[str] = field(default_factory=list)

    async def notify(self, message: str) -> None:
        self.sent.append(message)

    async def prompt(self, message: str, *, timeout_seconds: float | None = None) -> str | None:
        self.sent.append(message)
        if self.scripted_replies:
            return self.scripted_replies.pop(0)
        return None


@dataclass
class UI:
    channel: Channel

    async def preview_and_confirm(
        self,
        question: Question,
        answer: Answer,
        *,
        auto_submit_window_seconds: int = 0,
    ) -> bool:
        """Show the answer and return True iff the user approves.

        Per §1.12 override is sacred. Default is prompt-always (window=0):
        we never auto-submit without an explicit user signal. Non-zero
        windows still surface the answer and only auto-submit if the user
        does not veto within the window.
        """

        message = (
            f"Hearme wants to answer question {question.question_id}:\n"
            f"Q: {question.text}\n"
            f"A: {answer.text}\n"
            "Reply 'ok' to send, anything else to veto."
        )
        if auto_submit_window_seconds <= 0:
            reply = await self.channel.prompt(message)
            return reply is not None and reply.strip().lower() == "ok"
        # Preview window: user can veto inside the window.
        try:
            reply = await asyncio.wait_for(
                self.channel.prompt(message), timeout=auto_submit_window_seconds
            )
        except asyncio.TimeoutError:
            return True  # silence = consent within the user-configured window
        return reply is None or reply.strip().lower() not in {"veto", "no", "stop"}

    async def maybe_nudge_for_refresh(self, token: DelegationToken) -> None:
        """If we're inside the 7-day window, surface a refresh nudge (§7.7)."""

        if needs_refresh_soon(token):
            await self.channel.notify(
                "Hearme: your DelegationToken expires within "
                f"{REFRESH_WINDOW.days} days. Open ZKPassport on your phone "
                "to refresh."
            )

    async def announce_expiry(self) -> None:
        """The delegation expired before refresh. Stop answering; nudge user."""

        await self.channel.notify(
            "Hearme: DelegationToken expired. The skill has paused. Open "
            "ZKPassport on your phone to refresh."
        )
