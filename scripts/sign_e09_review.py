"""Human timeline-checkpoint signing tool for the E09 certification workflow.

The CreativeTimelineWorkflow stops at an in-workflow review checkpoint
(``awaiting_review``). This tool lets the human reviewer inspect the current
workflow state and, once the preview + timecode craft comparison is done, sign
approve / revise / reject by sending a ReviewSignal to the workflow.

The default run is a read-only status query; signing requires an explicit
``--decision``. This is the human Release-gate equivalent for the E09
certification path (``--auto-approve`` in accept_e09.py is machine-only).
"""

from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from temporalio.client import Client

from packages.foundation.settings import get_settings
from workflows.project.models import ReviewSignal
from workflows.timeline.creative_workflow import CreativeTimelineWorkflow


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="certification run UUID")
    parser.add_argument(
        "--decision",
        choices=("approve", "revise", "reject"),
        help="human decision; omit for read-only status query",
    )
    parser.add_argument("--note", default="", help="reviewer note (recorded in reasons)")
    args = parser.parse_args()

    run_id = UUID(args.run_id)
    workflow_id = f"e09-cert/{run_id}"
    review_id = f"review:{run_id}:timeline"

    client = await Client.connect(get_settings().temporal_target)
    handle = client.get_workflow_handle(workflow_id)
    status = await handle.query(CreativeTimelineWorkflow.get_status)  # type: ignore[attr-defined]
    if status is None:
        raise SystemExit(f"workflow {workflow_id} has no status (not found?)")

    print(f"workflow_id={workflow_id}")
    print(f"  state={status.state}  active_review_id={status.active_review_id}")
    print(f"  stages={dict(status.stage_states)}")
    print(f"  blocked_codes={status.blocked_codes}")
    for name, pointer in sorted(status.artifacts.items()):
        print(f"  artifact[{name}] = {pointer.artifact_id} v{pointer.version}")

    if status.active_review_id != review_id:
        expected = f"expected {review_id!r}"
        raise SystemExit(
            f"workflow is not at the expected review "
            f"({status.active_review_id!r} != {expected}); no signing performed"
        )
    if args.decision is None:
        print("== read-only: no decision sent ==")
        print("review the preview file, then re-run with --decision approve|revise|reject")
        return

    signal = ReviewSignal(
        review_id=review_id,
        target_version=1,
        decision=args.decision,
    )
    await handle.signal(CreativeTimelineWorkflow.submit_review_decision, signal)
    print(f"== {args.decision} signal sent; waiting for workflow settlement ==")

    elapsed = 0.0
    while elapsed < 900.0:
        current = await handle.query(CreativeTimelineWorkflow.get_status)  # type: ignore[attr-defined]
        if current is None:
            break
        print(f"  ... state={current.state} stages={dict(current.stage_states)}")
        if current.state in {"succeeded", "blocked", "rejected"}:
            print(f"== workflow {current.state} ==")
            if current.state != "succeeded":
                raise SystemExit(f"workflow did not succeed: {current.blocked_codes}")
            return
        await asyncio.sleep(3.0)
        elapsed += 3.0
    raise SystemExit("timed out waiting for workflow settlement")


if __name__ == "__main__":
    asyncio.run(main())
