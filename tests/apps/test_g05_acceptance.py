from pathlib import Path

import cv2
import numpy as np

from scripts.accept_g05 import visual_concurrency_probe


def test_g05_probe_is_bounded_and_has_no_production_authority(tmp_path: Path) -> None:
    path = tmp_path / "frame.png"
    assert cv2.imwrite(str(path), np.full((128, 64, 3), 127, dtype=np.uint8))
    result = visual_concurrency_probe(path, workers=2, requests=4)
    assert result["successes"] == 4
    assert result["provider_admission"] == "research"
    assert result["production_authority"] is False
