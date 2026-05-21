"""Aggregate helpers.

Accepted envelopes increment the ``aggregates`` row inside the same
transaction as the envelope INSERT, so a reader can never see
``total_answers`` drift from accepted envelope count.

Questions are yes/no, so ``by_predicate`` records *how* each cohort voted,
not just how many answered. The shape matches the schema comment and §3 of
ARCHITECTURE.md: one yes/no tally per (predicate_name, predicate_value)
pair across all envelopes for the question, e.g.
``{"region:EU": {"yes": 30, "no": 12}, "age_band:25-34": {"yes": 20, "no": 10}}``.
``total_answers`` remains the grand count of accepted envelopes.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Leading-word yes/no synonyms across the languages our demo questions use
# (en/de/fr/es/pt). The agent answers a yes/no question by leading with one of
# these; anything else classifies as ``None`` (counted in total_answers but not
# in a yes/no tally).
_YES_WORDS = {
    "yes", "y", "yeah", "yep", "yup", "sure", "absolutely",
    "ja", "oui", "si", "sí", "sim", "da",
}
_NO_WORDS = {
    "no", "n", "nope", "nah", "never",
    "nein", "non", "não", "nao",
}


def classify_vote(answer: Any) -> str | None:
    """Map a free-text answer to ``"yes"`` / ``"no"`` / ``None``.

    Looks only at the leading word so an elaboration ("Yes — auditability
    finally beats virality.") still classifies cleanly.
    """
    if not isinstance(answer, str):
        return None
    match = re.match(r"\w+", answer.strip().lower(), re.UNICODE)
    if not match:
        return None
    word = match.group(0)
    if word in _YES_WORDS:
        return "yes"
    if word in _NO_WORDS:
        return "no"
    return None


def _empty_tally() -> dict[str, int]:
    return {"yes": 0, "no": 0}


def compute_by_predicate(envelopes: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Pure function — easy to unit-test.

    Each envelope contributes its classified yes/no vote to every disclosed
    (predicate, value) bucket.
    """
    out: dict[str, dict[str, int]] = {}
    for env in envelopes:
        preds = env.get("disclosed_predicates") or {}
        if isinstance(preds, str):
            preds = json.loads(preds)
        vote = classify_vote(env.get("answer"))
        for k, v in preds.items():
            key = f"{k}:{v}"
            bucket = out.setdefault(key, _empty_tally())
            if vote in ("yes", "no"):
                bucket[vote] += 1
    return out
