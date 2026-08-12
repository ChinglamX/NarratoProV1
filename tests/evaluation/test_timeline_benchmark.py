from concurrent.futures import ThreadPoolExecutor

from packages.evaluation.timeline_benchmark import deterministic_parallel_signature


def test_parallel_fan_in_is_deterministic_across_completion_order() -> None:
    inputs = ("variant-c", "variant-a", "variant-b")
    with ThreadPoolExecutor(max_workers=3) as executor:
        completed = tuple(executor.map(lambda value: value, reversed(inputs)))
    expected = ("variant-a", "variant-b", "variant-c")
    assert deterministic_parallel_signature(completed) == expected
    assert deterministic_parallel_signature(inputs) == expected
