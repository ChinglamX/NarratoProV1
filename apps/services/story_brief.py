"""Persist an evidence-gated SpeechObservation -> FactSet -> StoryGraph chain."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import Engine

from packages.contracts import (
    ActorRef,
    ArtifactRef,
    ConfidenceRecord,
    ProviderIdentity,
    SpeechObservation,
    TranscriptSegment,
)
from packages.intelligence.facts import fuse_observations
from packages.intelligence.story_brief import StoryClaim, TranscriptCue, build_story_brief
from packages.persistence import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact


@dataclass(frozen=True, slots=True)
class PersistedStoryBrief:
    speech_observation: ArtifactRef
    fact_set: ArtifactRef
    story_graph: ArtifactRef


class StoryBriefPersistenceService:
    """Commit the three immutable artifacts in one database transaction."""

    def __init__(self, *, engine: Engine, artifacts: ArtifactRepository | None = None) -> None:
        self.engine = engine
        self.artifacts = artifacts or ArtifactRepository()

    def persist(
        self,
        *,
        project_id: UUID,
        run_id: UUID,
        source_audio_ref: ArtifactRef,
        raw_response_ref: ArtifactRef,
        resource_profile_ref: ArtifactRef,
        provider: ProviderIdentity,
        cues: tuple[TranscriptCue, ...],
        claims: tuple[StoryClaim, ...],
        unresolved: tuple[str, ...],
        trace_id: str,
        rights_class: str,
        actor: ActorRef,
    ) -> PersistedStoryBrief:
        if source_audio_ref.artifact_type != "AudioStem":
            raise ValueError("story brief source must reference AudioStem")
        if raw_response_ref.artifact_type != "RawProviderResponse":
            raise ValueError("story brief raw response must reference RawProviderResponse")

        unavailable = ConfidenceRecord.model_validate(
            {
                "score": None,
                "status": "unavailable",
                "method": "research-srt-import-no-calibration-v1",
                "applicable_scope": "episode-transcript:research:l1-review-required",
                "risk_class": "high",
                "opposing_factors": [
                    {
                        "code": "single-segment-asr",
                        "description": (
                            "Research SRT has no calibrated word alignment or diarization."
                        ),
                    }
                ],
            }
        )
        speech = SpeechObservation.model_validate(
            {
                "source_audio_ref": source_audio_ref,
                "raw_response_ref": raw_response_ref,
                "provider": provider,
                "vad_segments": (),
                "transcripts": tuple(
                    TranscriptSegment(
                        segment_id=uuid4(),
                        source_range=cue.source_range,
                        raw_text=cue.text,
                        normalized_text=cue.text,
                        language="zh-CN",
                        confidence=unavailable,
                    )
                    for cue in cues
                ),
                "status": "incomplete",
                "unavailable_reasons": ("word-alignment", "speaker-diarization"),
            }
        )

        speech_id, fact_id, story_id = uuid4(), uuid4(), uuid4()
        with self.engine.begin() as connection:
            speech_ref = commit_contract_artifact(
                connection,
                self.artifacts,
                artifact_id=speech_id,
                artifact_type="SpeechObservation",
                payload=speech,
                project_id=project_id,
                run_id=run_id,
                variant_id=None,
                trace_id=trace_id,
                actor=actor,
                producer_module="vc002-research-srt-import",
                module_version="1.0.0",
                resource_profile_ref=resource_profile_ref,
                rights_class=rights_class,
                inputs=(source_audio_ref, raw_response_ref),
                schema_version="1.5.0",
            )
            fact_placeholder = ArtifactRef.model_validate(
                {"artifact_id": fact_id, "version": 1, "artifact_type": "FactSet"}
            )
            fusion = fuse_observations(
                fact_set_ref=fact_placeholder,
                speech_ref=speech_ref,
                speech=speech,
            )
            fact_ref = commit_contract_artifact(
                connection,
                self.artifacts,
                artifact_id=fact_id,
                artifact_type="FactSet",
                payload=fusion.fact_set,
                project_id=project_id,
                run_id=run_id,
                variant_id=None,
                trace_id=trace_id,
                actor=actor,
                producer_module="vc002-observation-fact-fusion",
                module_version="1.0.0",
                resource_profile_ref=resource_profile_ref,
                rights_class=rights_class,
                inputs=(speech_ref,),
                schema_version="2.0.0",
            )
            story = build_story_brief(
                fact_ref=fact_ref,
                transcript_ref=speech_ref,
                cues=cues,
                claims=claims,
                unresolved=unresolved,
            )
            story_ref = commit_contract_artifact(
                connection,
                self.artifacts,
                artifact_id=story_id,
                artifact_type="StoryGraph",
                payload=story,
                project_id=project_id,
                run_id=run_id,
                variant_id=None,
                trace_id=trace_id,
                actor=actor,
                producer_module="vc002-evidence-gated-story-brief",
                module_version="1.0.0",
                resource_profile_ref=resource_profile_ref,
                rights_class=rights_class,
                inputs=(fact_ref,),
                schema_version="2.1.0",
            )
        return PersistedStoryBrief(speech_ref, fact_ref, story_ref)
