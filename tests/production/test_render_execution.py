from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef
from packages.contracts.render_release import RenderOperation, RenderPlanContract
from packages.production import render


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def plan(*, blocked: bool = False) -> RenderPlanContract:
    return RenderPlanContract(
        conformed_timeline_ref=ref("MasterTimeline"),
        mixed_audio_ref=ref("MixedAudio"),
        ass_artifact_ref=ref("ASSArtifact"),
        platform_profile_ref=ref("ConfigArtifact"),
        toolchain_version="ffmpeg-8.1.2",
        mode="final",
        operations=(
            RenderOperation(
                operation_id=uuid4(),
                operation_type="encode",
                input_refs=(ref("MasterTimeline"),),
                parameters={},
                cache_key="encode-1",
            ),
        ),
        expected_duration={"value": 1, "rate_num": 1},
        output_spec={"codec": "h264"},
        checksum="sha256:plan",
        blocker_codes=("upstream",) if blocked else (),
    )


def test_render_rejects_blocked_or_non_ffmpeg_command(tmp_path: Path) -> None:
    with pytest.raises(render.RenderExecutionError, match="blocked"):
        render.execute_ffmpeg_plan(
            plan=plan(blocked=True),
            plan_ref=ref("RenderPlan"),
            command=("ffmpeg",),
            output_path=tmp_path / "out.mp4",
            ffmpeg_version="8.1.2",
            attempt=1,
            heartbeat=lambda _event: None,
        )
    with pytest.raises(render.RenderExecutionError, match="ffmpeg directly"):
        render.execute_ffmpeg_plan(
            plan=plan(),
            plan_ref=ref("RenderPlan"),
            command=("shell", "ffmpeg"),
            output_path=tmp_path / "out.mp4",
            ffmpeg_version="8.1.2",
            attempt=1,
            heartbeat=lambda _event: None,
        )


def test_render_atomically_commits_checksum_and_heartbeats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events = []

    def fake_run(command, **_kwargs):
        Path(command[-1]).write_bytes(b"final-media")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(render.subprocess, "run", fake_run)
    output = tmp_path / "final.mp4"
    report = render.execute_ffmpeg_plan(
        plan=plan(),
        plan_ref=ref("RenderPlan"),
        command=("ffmpeg", "-y"),
        output_path=output,
        ffmpeg_version="8.1.2",
        attempt=1,
        heartbeat=events.append,
    )
    assert output.read_bytes() == b"final-media"
    assert report.succeeded and report.output_checksum == render.sha256_file(output)
    assert events[-1]["complete"] is True
