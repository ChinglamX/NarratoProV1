from uuid import uuid4

from packages.contracts import ArtifactRef, MasterTimeline, TimelineItem, TimelinePatch


def rational(value: int, rate: int = 25) -> dict[str, int]:
    return {"value": value, "rate_num": rate}


def artifact_ref(kind: str) -> dict[str, object]:
    return {"artifact_id": uuid4(), "version": 1, "artifact_type": kind}


def item(*, start: int = 0, duration: int = 25, item_type: str = "clip") -> TimelineItem:
    payload: dict[str, object] = {
        "item_id": uuid4(),
        "item_version": 1,
        "item_type": item_type,
        "timeline_range": {"start": rational(start), "duration": rational(duration)},
    }
    if item_type == "clip":
        payload |= {
            "source_ref": artifact_ref("SourceMedia"),
            "source_range": {"start": rational(start), "duration": rational(duration)},
        }
    elif item_type == "text":
        payload["content_ref"] = "narration.line.1"
    return TimelineItem.model_validate(payload)


def timeline(*items: TimelineItem) -> MasterTimeline:
    if not items:
        items = (item(),)
    return MasterTimeline.model_validate(
        {
            "timeline_id": uuid4(),
            "lifecycle": "draft",
            "rate_num": 25,
            "global_start": rational(0),
            "duration": rational(100),
            "tracks": [
                {
                    "track_id": uuid4(),
                    "kind": "video",
                    "order": 0,
                    "items": [value.model_dump(mode="json") for value in items],
                }
            ],
            "metadata_namespace_version": "1.0.0",
        }
    )


def patch(target: TimelineItem, op: str, payload: dict[str, object]) -> TimelinePatch:
    return TimelinePatch.model_validate(
        {
            "patch_id": uuid4(),
            "base_timeline": artifact_ref("MasterTimeline"),
            "operations": [
                {
                    "operation_id": uuid4(),
                    "op": op,
                    "target_item_id": target.item_id,
                    "expected_item_version": target.item_version,
                    "payload": payload,
                }
            ],
            "author": {"kind": "human", "id": "editor"},
            "reason": "timeline test",
        }
    )


def typed_ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate(artifact_ref(kind))
