"""Temporal worker bootstrap; workflows are registered incrementally by Epic."""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from packages.foundation.settings import get_settings
from workflows.intelligence import (
    StoryReasoningWorkflow,
    assemble_story_graph_activity,
    build_causal_graph_activity,
    build_character_state_activity,
    build_event_set_activity,
)
from workflows.media import MediaIngestWorkflow, ingest_media_activity
from workflows.production.activities import (
    build_subtitle_activity,
    plan_mix_activity,
    render_ass_activity,
)
from workflows.production.render_activities import (
    execute_render_activity,
    technical_qc_activity,
)
from workflows.production.render_workflow import RenderWorkflow
from workflows.production.tts_activities import synthesize_voice_activity
from workflows.production.workflow import MediaProductionPlanningWorkflow
from workflows.project import ProjectRunWorkflow, execute_conformance_activity
from workflows.speech import SpeechObservationWorkflow, process_speech_activity
from workflows.timeline import TimelinePreviewWorkflow, render_preview_activity
from workflows.timeline.creative_activities import (
    assemble_timeline_activity,
    plan_rhythm_activity,
    plan_visual_activity,
    render_media_preview_activity,
    review_narration_activity,
)
from workflows.timeline.creative_workflow import CreativeTimelineWorkflow
from workflows.visual import VisualObservationWorkflow, process_visual_activity

CONTROL_TASK_QUEUE = "control"
WORKER_BUILD_ID = "narratopro-e03-v1"


async def serve() -> None:
    settings = get_settings()
    client = await Client.connect(
        settings.temporal_target,
        namespace=settings.temporal_namespace,
    )
    worker = Worker(
        client,
        task_queue=CONTROL_TASK_QUEUE,
        workflows=[
            ProjectRunWorkflow,
            TimelinePreviewWorkflow,
            CreativeTimelineWorkflow,
            MediaIngestWorkflow,
            SpeechObservationWorkflow,
            VisualObservationWorkflow,
            StoryReasoningWorkflow,
            MediaProductionPlanningWorkflow,
            RenderWorkflow,
        ],
        activities=[
            execute_conformance_activity,
            render_preview_activity,
            plan_visual_activity,
            plan_rhythm_activity,
            review_narration_activity,
            assemble_timeline_activity,
            render_media_preview_activity,
            ingest_media_activity,
            process_speech_activity,
            process_visual_activity,
            build_event_set_activity,
            build_character_state_activity,
            build_causal_graph_activity,
            assemble_story_graph_activity,
            plan_mix_activity,
            build_subtitle_activity,
            render_ass_activity,
            execute_render_activity,
            technical_qc_activity,
            synthesize_voice_activity,
        ],
        build_id=WORKER_BUILD_ID,
        use_worker_versioning=False,
    )
    await worker.run()


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
