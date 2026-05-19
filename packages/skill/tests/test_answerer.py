"""Answerer tests — fake LLM client, no live calls (§12)."""

from __future__ import annotations

from hearme_skill.answerer import answer
from hearme_skill.llm.client import FakeLLMClient, LLMResponse
from hearme_skill.memory.mem0_stub import Mem0StubProvider
from hearme_skill.persona import project


def test_answerer_uses_persona_facts(question):
    persona = project(question, Mem0StubProvider())
    llm = FakeLLMClient()
    out = answer(persona, question, llm)
    # Default fake reply concatenates persona facts; assert one shows up.
    assert "single-origin" in out.text


def test_answerer_recorded_response(question):
    persona = project(question, Mem0StubProvider())
    llm = FakeLLMClient(
        responses={
            question.text: LLMResponse(
                text="I prefer single-origin in the morning, blends in the afternoon.",
                rationale="recalled morning vs afternoon preference",
            )
        }
    )
    out = answer(persona, question, llm)
    assert out.text.startswith("I prefer single-origin")
    assert out.rationale == "recalled morning vs afternoon preference"


def test_answerer_never_makes_live_calls(question):
    """The FakeLLMClient is the only client touched. Assert via call log."""

    persona = project(question, Mem0StubProvider())
    llm = FakeLLMClient()
    answer(persona, question, llm)
    assert len(llm.calls) == 1


def test_answerer_returns_local_rationale(question):
    persona = project(question, Mem0StubProvider())
    llm = FakeLLMClient(
        responses={question.text: LLMResponse(text="OK", rationale="thinking out loud")}
    )
    out = answer(persona, question, llm)
    assert out.rationale == "thinking out loud"
