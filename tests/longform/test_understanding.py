import pytest

from packages.longform.story_index import EventFunction
from packages.longform.understanding import (
    EventProposal,
    TranscriptSegment,
    VisualObservation,
    compile_event_proposals,
)


def transcript(text: str = "这里面是五十万") -> TranscriptSegment:
    return TranscriptSegment("t1", 1, 10, 12, text, "speaker-1")


def visual() -> VisualObservation:
    return VisualObservation("v1", 1, 10, 12, "买方把现金箱放在桌面")


def proposal(description: str = "买方给出五十万现金报价") -> EventProposal:
    return EventProposal(
        event_id="cash-offer",
        episode=1,
        order_in_episode=1,
        description=description,
        function=EventFunction.CLIMAX,
        character_refs=("buyer",),
        transcript_refs=("t1",),
        visual_refs=("v1",),
        importance=5,
        visual_payoff=5,
        original_audio_value=5,
    )


def test_evidence_grounded_proposal_compiles() -> None:
    events = compile_event_proposals(
        proposals=(proposal(),),
        transcripts=(transcript(),),
        visuals=(visual(),),
        known_character_refs=frozenset({"buyer"}),
    )
    assert events[0].has_dialogue_evidence and events[0].has_visual_evidence


def test_core_event_requires_dialogue_and_visual() -> None:
    missing_visual = proposal().__class__(**{**proposal().__dict__, "visual_refs": ()})
    with pytest.raises(ValueError, match="both dialogue and visual"):
        compile_event_proposals(
            proposals=(missing_visual,),
            transcripts=(transcript(),),
            visuals=(visual(),),
            known_character_refs=frozenset({"buyer"}),
        )


def test_unsupported_number_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported numeric"):
        compile_event_proposals(
            proposals=(proposal("买方给出一百万现金报价"),),
            transcripts=(transcript(),),
            visuals=(visual(),),
            known_character_refs=frozenset({"buyer"}),
        )
