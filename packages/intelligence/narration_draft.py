"""Deterministic validation for research LLM narration drafts.

LLM-generated narration is a *draft* candidate: it must be evidence-grounded
and must pass fail-closed rules before it is presented to the human reviewer.
The final decision stays at the L1 narration boundary (the E09 timeline
checkpoint / NarrationSourcePort human-approved line sets). This module only
validates; it never fabricates or approves text.
"""

from __future__ import annotations

from collections.abc import Sequence

# Project rules: identity is unproven (no character names), no unsupported
# psychology, no verbatim dialogue repetition (AGENTS.md rule 7).
DEFAULT_FORBIDDEN_TOKENS = (
    "虎哥",  # source-dialogue name; identity unproven
    "那小子",  # source-dialogue referent; not an approved identity
    "他心里想",
    "她心里想",
    "注定",
)


def _normalize(value: str) -> str:
    return "".join(character for character in value if character.isalnum()).lower()


def validate_narration_draft(
    text: str,
    *,
    dialogue_excerpts: Sequence[str],
    forbidden_tokens: Sequence[str] = DEFAULT_FORBIDDEN_TOKENS,
) -> list[str]:
    """Return the list of rule violations; empty list means the draft is usable.

    Fail-closed: an empty or ambiguous draft, any forbidden token, or a draft
    that repeats source dialogue verbatim is rejected with an explicit code.
    """
    violations: list[str] = []
    if not text or not text.strip():
        violations.append("empty")
        return violations
    for token in forbidden_tokens:
        if token in text:
            violations.append(f"forbidden-token:{token}")
    normalized = _normalize(text)
    for excerpt in dialogue_excerpts:
        if normalized == _normalize(excerpt):
            violations.append("dialogue-repetition")
    return violations
