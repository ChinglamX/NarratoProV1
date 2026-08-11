from packages.evaluation import ShadowPrediction


def test_missing_version_is_incomplete_and_never_routes() -> None:
    prediction = ShadowPrediction("story", {"event": 1}, {"score": 0.8}, "m1", None, "c1")
    example = prediction.calibration_example(
        corrected={"event": 2}, reviewer_id="reviewer", review_duration_ms=1200
    )
    assert example["status"] == "incomplete"
    assert example["routing_authority"] is False


def test_all_versions_create_complete_example() -> None:
    prediction = ShadowPrediction("story", {}, {}, "m1", "p1", "c1")
    assert (
        prediction.calibration_example(corrected={}, reviewer_id="r", review_duration_ms=1)[
            "status"
        ]
        == "complete"
    )
