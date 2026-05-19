"""Real Hermes-backed LLM client.

Adapter that bridges the skill's ``LLMClient`` protocol to the Hermes Agent
runtime (``hermes-agent`` on PyPI, MIT, Nous Research). The skill never
imports a specific LLM SDK directly; Hermes handles model selection,
memory injection, and the OpenAI-compatible call to OpenRouter.

This module is *optional*. It is only imported when
``HEARME_USE_HERMES=1`` and ``hermes-agent`` is installed. Otherwise
``dev_runner`` falls back to ``FakeLLMClient`` (per ARCHITECTURE.md §12,
"never live LLM in CI by default").

Privacy posture (ARCHITECTURE.md §1.2, §1.4, §7.4):

* This client receives only the ``LLMRequest`` — question text, persona
  facts, style hints. It never sees the DelegationToken or
  ``unique_identifier``. ``test_identity_inference_separation.py``
  asserts this from the answerer side.
* Memory retrieval happens inside Hermes; the skill does not expose raw
  memory IDs or source quotes to the broker.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from .client import LLMRequest, LLMResponse

log = logging.getLogger("hearme_skill.llm.hermes")


# A deliberately cheap default. Users can override via HEARME_HERMES_MODEL.
# OpenRouter exposes Gemini Flash Lite as `google/gemini-2.5-flash-lite`
# — note: NO ``openrouter/`` prefix; Hermes routes by the ``provider``
# argument instead.
_DEFAULT_MODEL = "google/gemini-2.5-flash-lite"
_DEFAULT_PROVIDER = "openrouter"


def _import_aiagent() -> Any:
    """Locate ``AIAgent`` across Hermes versions.

    The class is imported from ``run_agent`` in the Python-library docs
    but Hermes ships ``hermes_agent`` as the namespaced package name. Try
    both so we don't lock the skill to one Hermes minor version.
    """

    last_err: Exception | None = None
    for module_name in ("run_agent", "hermes_agent.run_agent", "hermes_agent"):
        try:
            mod = __import__(module_name, fromlist=["AIAgent"])
            if hasattr(mod, "AIAgent"):
                return mod.AIAgent
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue
    raise ImportError(
        "Could not import Hermes's AIAgent. Install `pip install hermes-agent` "
        "and ensure the version exposes `AIAgent` via `run_agent` or "
        f"`hermes_agent`. Last error: {last_err!r}"
    )


def _resolve_openrouter_key() -> str | None:
    """Return the OpenRouter API key from env, accepting two common spellings.

    The user's ``.env`` ships as ``OPEN_ROUTER_API_KEY`` (with the extra
    underscore); upstream tools also recognise ``OPENROUTER_API_KEY``. We
    accept either and normalise to the upstream spelling for Hermes.
    """

    return os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPEN_ROUTER_API_KEY")


def _build_prompt(req: LLMRequest) -> str:
    """Compose the message we hand to Hermes.

    Hermes's own memory layer will splice in the user's prior conversation
    context — we just provide the question, any precomputed persona facts
    (which v0 may leave empty when Hermes is the memory source), and a
    short style nudge. Identity material is structurally excluded from
    ``LLMRequest``.
    """

    parts: list[str] = []
    parts.append(
        "You are answering on behalf of the user, in their voice, "
        "based ONLY on what you actually know about them from prior "
        "conversations. Do not invent preferences. If you do not know, "
        "say so."
    )
    if req.persona_facts:
        joined = "; ".join(req.persona_facts)
        parts.append(f"Known preferences (sanitized): {joined}.")
    if req.style_hints:
        parts.append(f"Style hints: {', '.join(req.style_hints)}.")
    if req.style_guide:
        parts.append(req.style_guide)
    parts.append("Keep the answer under 3 sentences.")
    parts.append(f"Question: {req.question_text}")
    return "\n\n".join(parts)


@dataclass
class HermesLLMClient:
    """LLMClient implementation backed by ``hermes_agent.AIAgent``.

    Construction is cheap; the AIAgent instance is created lazily on first
    ``complete()`` so importing this module never spins up a model.
    """

    model: str = field(default_factory=lambda: os.environ.get("HEARME_HERMES_MODEL", _DEFAULT_MODEL))
    provider: str = field(default_factory=lambda: os.environ.get("HEARME_HERMES_PROVIDER", _DEFAULT_PROVIDER))
    skip_memory: bool = False
    # When True (default), ``complete()`` runs without passing
    # ``conversation_history`` — Hermes's memory provider is responsible
    # for retrieving prior context via prefetch + auto-extracted facts.
    # When False, the in-process turn buffer is replayed every call —
    # cheap for the first few turns, prohibitively expensive at scale.
    use_persistent_memory: bool = True
    # Allow tests / dev runs to share one AIAgent across calls so memory
    # accumulates. In production this is the desired behavior anyway.
    _agent: Any = None
    _conversation_history: list[dict[str, str]] = field(default_factory=list)
    _session_message_buffer: list[dict[str, str]] = field(default_factory=list)

    def _ensure_agent(self) -> Any:
        if self._agent is not None:
            return self._agent
        AIAgent = _import_aiagent()
        key = _resolve_openrouter_key()
        if key and not os.environ.get("OPENROUTER_API_KEY"):
            # Hermes reads OPENROUTER_API_KEY natively; normalise the
            # OPEN_ROUTER_API_KEY spelling for it.
            os.environ["OPENROUTER_API_KEY"] = key
        # ``quiet_mode=True`` per Hermes's Python-library guide: "Always set
        # quiet_mode=True when embedding Hermes in your own code." Pass the
        # OpenRouter key explicitly so Hermes doesn't depend on its own
        # config.yaml — keeps the skill self-contained for the e2e test.
        self._agent = AIAgent(
            model=self.model,
            provider=self.provider,
            api_key=key,
            quiet_mode=True,
            skip_memory=self.skip_memory,
        )
        log.info(
            "hermes AIAgent ready (provider=%s, model=%s, skip_memory=%s)",
            self.provider, self.model, self.skip_memory,
        )
        return self._agent

    def reset_conversation(self) -> None:
        """Drop the in-process turn history (memory on disk is untouched)."""

        self._conversation_history = []
        self._session_message_buffer = []

    def chat(self, user_message: str, *, replay_history: bool = False) -> str:
        """Run one conversational turn against Hermes.

        ``replay_history=True`` passes the in-process buffer back to
        Hermes (cheap & deterministic for short demos but O(turns) in
        token cost — what we *don't* want at scale). The default
        ``False`` mode passes only the new user message; Hermes's
        configured memory provider injects context via its
        ``prefetch`` hook.

        Used by ``hearme-skill hermes-chat`` and the e2e seed step.
        """

        agent = self._ensure_agent()
        history_arg = list(self._conversation_history) if replay_history else []
        if hasattr(agent, "run_conversation"):
            result = agent.run_conversation(
                user_message=user_message,
                conversation_history=history_arg,
            )
            text = result.get("final_response", "") if isinstance(result, dict) else str(result)
            new_history = (
                result.get("messages", []) if isinstance(result, dict) else []
            )
            if new_history:
                self._conversation_history = list(new_history)
            else:
                self._conversation_history.append({"role": "user", "content": user_message})
                self._conversation_history.append({"role": "assistant", "content": text})
            # Always buffer the raw exchange so ``commit_memory()`` has
            # something the provider's on_session_end can read.
            self._session_message_buffer.append({"role": "user", "content": user_message})
            self._session_message_buffer.append({"role": "assistant", "content": text})
            return text
        if hasattr(agent, "chat"):
            text = agent.chat(user_message)
            self._conversation_history.append({"role": "user", "content": user_message})
            self._conversation_history.append({"role": "assistant", "content": text})
            self._session_message_buffer.append({"role": "user", "content": user_message})
            self._session_message_buffer.append({"role": "assistant", "content": text})
            return text
        raise AttributeError(
            "Hermes AIAgent exposes neither `run_conversation` nor `chat`; "
            "this Hermes version is unsupported."
        )

    def commit_memory(self) -> None:
        """Trigger Hermes's ``on_session_end`` so the memory provider
        flushes / auto-extracts facts from the buffered turns.

        Holographic's ``auto_extract: true`` runs preference / decision
        regexes over the user turns and stores matches as durable facts
        keyed for later prefetch.
        """

        agent = self._ensure_agent()
        if not hasattr(agent, "commit_memory_session"):
            return
        agent.commit_memory_session(list(self._session_message_buffer))
        # Buffer is one session's worth; once committed, start fresh so
        # the next commit doesn't re-extract the same turns.
        self._session_message_buffer = []

    # ---- LLMClient protocol -------------------------------------------------

    def complete(self, req: LLMRequest) -> LLMResponse:
        """Run a single LLM call.

        With ``use_persistent_memory=True`` (default) we hand Hermes
        only the new question — its memory provider's ``prefetch`` hook
        retrieves relevant prior facts and Hermes splices them into the
        system prompt. That keeps per-turn token cost O(retrieval
        budget) instead of O(conversation length).
        """

        prompt = _build_prompt(req)
        try:
            text = self.chat(prompt, replay_history=not self.use_persistent_memory)
        except Exception:  # noqa: BLE001
            log.exception("hermes completion failed")
            raise
        # Rationale stays empty: anything we'd put here would also need to
        # respect the local-only contract; Hermes doesn't surface a usable
        # rationale via the public API yet.
        return LLMResponse(text=str(text).strip(), rationale="")
