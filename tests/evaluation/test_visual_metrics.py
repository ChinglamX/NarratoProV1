import pytest

from packages.contracts import BoundingBox
from packages.evaluation import (
    detection_precision_recall,
    ocr_character_error_rate,
    tracking_id_switch_rate,
)


def box(x: float) -> BoundingBox:
    return BoundingBox(x_min=x, y_min=0.1, x_max=x + 0.2, y_max=0.5)


def test_visual_metrics_are_capability_specific() -> None:
    assert ocr_character_error_rate("欠条", "欠条") == 0
    assert detection_precision_recall([box(0.1)], [box(0.1)]) == (1.0, 1.0)
    assert tracking_id_switch_rate([("a", "1"), ("a", "2")]) == 1.0
    with pytest.raises(ValueError, match="requires assignments"):
        tracking_id_switch_rate([])
