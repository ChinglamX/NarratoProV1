import pytest

from packages.control.visual_resources import VisualResourceExhausted, admitted_batch_size


def test_visual_batch_admission_shrinks_and_fails_closed() -> None:
    assert (
        admitted_batch_size(
            requested=16,
            bytes_per_frame=100,
            available_accelerator_bytes=1_000,
            reserve_ratio=0.2,
        )
        == 8
    )
    with pytest.raises(VisualResourceExhausted):
        admitted_batch_size(
            requested=1,
            bytes_per_frame=101,
            available_accelerator_bytes=100,
            reserve_ratio=0,
        )
