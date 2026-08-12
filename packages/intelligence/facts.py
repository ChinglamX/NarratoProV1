"""Conservative Observation-to-Fact fusion; interpretation belongs to Story."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

from packages.contracts import (
    ArtifactRef,
    EvidenceBundle,
    EvidenceLink,
    Fact,
    FactSet,
    FactStatus,
    FactType,
    FusionConflict,
    FusionReport,
    RationalTime,
    SpeechObservation,
    TimeRange,
    VisualObservation,
)


def _evidence(
    source: ArtifactRef,
    source_range: TimeRange,
    evidence_type: str,
    excerpt: str,
    id_factory: Callable[[], UUID],
) -> EvidenceLink:
    return EvidenceLink.model_validate(
        {
            "evidence_id": id_factory(),
            "source": source,
            "source_range": source_range,
            "evidence_type": evidence_type,
            "excerpt": excerpt,
        }
    )


def fuse_observations(
    *,
    fact_set_ref: ArtifactRef,
    speech_ref: ArtifactRef | None = None,
    speech: SpeechObservation | None = None,
    visual_ref: ArtifactRef | None = None,
    visual: VisualObservation | None = None,
    frame_duration: RationalTime | None = None,
    id_factory: Callable[[], UUID] = uuid4,
) -> FusionReport:
    """Create only directly observable facts and preserve unavailable partitions."""

    if (speech_ref is None) != (speech is None) or (visual_ref is None) != (visual is None):
        raise ValueError("observation payload and ref must be provided together")
    frame_duration = frame_duration or RationalTime(value=1, rate_num=25)
    source_refs = tuple(item for item in (speech_ref, visual_ref) if item is not None)
    facts: list[Fact] = []
    bundles: list[EvidenceBundle] = []
    conflicts: list[FusionConflict] = []
    incomplete: list[str] = []

    if speech is not None and speech_ref is not None:
        if speech.status.value != "complete":
            incomplete.append("speech")
        for segment in speech.transcripts:
            link = _evidence(
                speech_ref, segment.source_range, "dialogue", segment.raw_text, id_factory
            )
            item = Fact(
                fact_id=id_factory(),
                fact_type=FactType.DIALOGUE,
                subject_ref=segment.speaker_cluster_id,
                value={"raw_text": segment.raw_text, "normalized_text": segment.normalized_text},
                source_range=segment.source_range,
                evidence=(link,),
                provider=speech.provider,
                confidence=segment.confidence,
                status=FactStatus.OBSERVED,
            )
            facts.append(item)
            bundles.append(EvidenceBundle(target_ref=fact_set_ref, links=(link,)))

    if visual is not None and visual_ref is not None:
        if visual.status.value != "complete":
            incomplete.extend(visual.unavailable_capabilities or ("visual",))
        for ocr_item in visual.ocr:
            source_range = TimeRange(start=ocr_item.frame.source_time, duration=frame_duration)
            link = _evidence(visual_ref, source_range, "ocr", ocr_item.text, id_factory)
            item = Fact(
                fact_id=id_factory(),
                fact_type=FactType.OCR,
                value={"text": ocr_item.text, "kind": ocr_item.kind.value},
                source_range=source_range,
                evidence=(link,),
                provider=ocr_item.provider,
                confidence=ocr_item.confidence,
                status=FactStatus.OBSERVED,
            )
            facts.append(item)
            bundles.append(EvidenceBundle(target_ref=fact_set_ref, links=(link,)))
        for detection in visual.detections:
            source_range = TimeRange(start=detection.frame.source_time, duration=frame_duration)
            link = _evidence(visual_ref, source_range, "visual", detection.label, id_factory)
            item = Fact(
                fact_id=id_factory(),
                fact_type=FactType.PERSON if detection.label == "person" else FactType.ENTITY,
                value={"label": detection.label, "region": detection.region.model_dump()},
                source_range=source_range,
                evidence=(link,),
                provider=detection.provider,
                confidence=detection.confidence,
                status=FactStatus.OBSERVED,
            )
            facts.append(item)
            bundles.append(EvidenceBundle(target_ref=fact_set_ref, links=(link,)))
        # VLM inferred/unknown claims are intentionally excluded from Fact.

    # ASR and burned-in subtitles are correlated sources; disagreement remains explicit.
    dialogue = [item for item in facts if item.fact_type.value == "dialogue"]
    subtitles = []
    for item in facts:
        if (
            item.fact_type.value == "ocr"
            and isinstance(item.value, dict)
            and item.value.get("kind") == "burned_in_subtitle"
        ):
            subtitles.append(item)
    for spoken in dialogue:
        for subtitle in subtitles:
            overlaps = (
                spoken.source_range.start.seconds < subtitle.source_range.end_seconds
                and subtitle.source_range.start.seconds < spoken.source_range.end_seconds
            )
            spoken_value = spoken.value if isinstance(spoken.value, dict) else {}
            subtitle_value = subtitle.value if isinstance(subtitle.value, dict) else {}
            spoken_text = str(spoken_value.get("normalized_text", "")).replace(" ", "")
            subtitle_text = str(subtitle_value.get("text", "")).replace(" ", "")
            if overlaps and spoken_text and subtitle_text and spoken_text != subtitle_text:
                conflicts.append(
                    FusionConflict(
                        conflict_id=id_factory(),
                        conflict_type="asr-ocr-text-disagreement",
                        source_range=spoken.source_range,
                        fact_ids=(spoken.fact_id, subtitle.fact_id),
                        supporting=spoken.evidence,
                        opposing=subtitle.evidence,
                        detail="Overlapping ASR and burned-in subtitle text disagree",
                    )
                )
    fact_set = FactSet(
        source_refs=source_refs,
        facts=tuple(facts),
        incomplete=bool(incomplete),
        unavailable_partitions=tuple(sorted(set(incomplete))),
    )
    return FusionReport(
        fact_set=fact_set,
        evidence_bundles=tuple(bundles),
        conflicts=tuple(conflicts),
        incomplete_partitions=fact_set.unavailable_partitions,
    )
