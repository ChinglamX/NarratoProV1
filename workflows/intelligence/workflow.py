from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.intelligence.activities import (
        assemble_story_graph_activity,
        build_causal_graph_activity,
        build_character_state_activity,
        build_event_set_activity,
    )
    from workflows.intelligence.models import StoryReasoningInput, StoryReasoningStatus


@workflow.defn
class StoryReasoningWorkflow:
    def __init__(self) -> None:
        self._status: StoryReasoningStatus | None = None

    @workflow.run
    async def run(self, request: StoryReasoningInput) -> StoryReasoningStatus:
        retry = RetryPolicy(maximum_attempts=3)
        self._status = StoryReasoningStatus(request.run_id, "processing", "event_set")
        event_result = await workflow.execute_activity(
            build_event_set_activity,
            request,
            start_to_close_timeout=timedelta(hours=1),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=retry,
        )
        self._status.event_set = event_result.output
        self._status.current_stage = "character_state"
        state_result = await workflow.execute_activity(
            build_character_state_activity,
            request,
            start_to_close_timeout=timedelta(hours=1),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=retry,
        )
        self._status.character_state_graph = state_result.output
        self._status.current_stage = "causal_graph"
        causal_result = await workflow.execute_activity(
            build_causal_graph_activity,
            request,
            start_to_close_timeout=timedelta(hours=1),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=retry,
        )
        self._status.causal_graph = causal_result.output
        self._status.current_stage = "story_graph"
        story_result = await workflow.execute_activity(
            assemble_story_graph_activity,
            request,
            start_to_close_timeout=timedelta(hours=1),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=retry,
        )
        self._status.story_graph = story_result.output
        self._status.current_stage = "complete"
        self._status.state = "succeeded"
        return self._status

    @workflow.query
    def status(self) -> StoryReasoningStatus | None:
        return self._status
