"""Unit tests for research LLM narration draft validation."""

# ruff: noqa: RUF001 - CJK draft strings are intentional

from packages.intelligence.narration_draft import validate_narration_draft

DIALOGUE = ("这张卡里有三十万，密码，六个八", "三十万这两样我都要了")


def test_valid_draft_passes() -> None:
    assert (
        validate_narration_draft("一张卡装着三十万和六个八的密码。", dialogue_excerpts=DIALOGUE)
        == []
    )


def test_empty_draft_fails_closed() -> None:
    assert validate_narration_draft("", dialogue_excerpts=DIALOGUE) == ["empty"]
    assert validate_narration_draft("   ", dialogue_excerpts=DIALOGUE) == ["empty"]


def test_forbidden_identity_token_rejected() -> None:
    violations = validate_narration_draft("虎哥下令盯住他。", dialogue_excerpts=DIALOGUE)
    assert "forbidden-token:虎哥" in violations


def test_forbidden_psychology_token_rejected() -> None:
    violations = validate_narration_draft("他心里想，这笔钱不能还。", dialogue_excerpts=DIALOGUE)
    assert "forbidden-token:他心里想" in violations


def test_dialogue_repetition_rejected() -> None:
    violations = validate_narration_draft(
        "这张卡里有三十万，密码，六个八", dialogue_excerpts=DIALOGUE
    )
    assert "dialogue-repetition" in violations


def test_partial_dialogue_quotation_is_allowed() -> None:
    # A draft may reference the amount without repeating the whole line.
    assert (
        validate_narration_draft("卡里的三十万和密码，落到了买主手里。", dialogue_excerpts=DIALOGUE)
        == []
    )
