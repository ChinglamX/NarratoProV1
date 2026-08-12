"""Fail-closed visual micro-batch sizing for accelerator memory protection."""

from __future__ import annotations


class VisualResourceExhausted(RuntimeError):
    pass


def admitted_batch_size(
    *, requested: int, bytes_per_frame: int, available_accelerator_bytes: int, reserve_ratio: float
) -> int:
    if requested <= 0 or bytes_per_frame <= 0 or available_accelerator_bytes < 0:
        raise ValueError("visual resource inputs must be positive")
    if not 0.0 <= reserve_ratio < 1.0:
        raise ValueError("reserve_ratio must be in [0, 1)")
    usable = int(available_accelerator_bytes * (1.0 - reserve_ratio))
    admitted = min(requested, usable // bytes_per_frame)
    if admitted < 1:
        raise VisualResourceExhausted("no visual frame fits accelerator memory budget")
    return admitted
