"""Question eligibility checks derived from signed delegation predicates."""

from __future__ import annotations

from typing import Any


def _norm(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped.upper() if stripped else None


def is_scope_eligible(
    *,
    question: dict[str, Any],
    disclosed_predicates: dict[str, str],
) -> bool:
    """Return whether this token is eligible to answer this question.

    v0 supports the geographic scopes already present in the questions table:
    worldwide, continent, and country. The signed DelegationToken predicates
    are the trust source. We accept ``continent`` or legacy ``region`` for
    continent-level matching because the seed data and early tokens used
    ``region`` to mean continent code.
    """

    scope = (question.get("scope") or "worldwide").strip().lower()
    if scope == "worldwide":
        return True

    country = _norm(disclosed_predicates.get("country"))
    continent = _norm(
        disclosed_predicates.get("continent") or disclosed_predicates.get("region")
    )

    if scope == "country":
        expected_country = _norm(question.get("country"))
        return bool(expected_country and country == expected_country)

    if scope == "continent":
        expected_continent = _norm(question.get("continent"))
        return bool(expected_continent and continent == expected_continent)

    return False
