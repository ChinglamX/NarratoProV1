from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.services.strategy_inputs import ApprovedStoryRequired, StrategyInputService


class Engine:
    class Context:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return None

    def connect(self):
        return self.Context()


def test_strategy_input_requires_approved_story_pointer() -> None:
    service = StrategyInputService(Engine())  # type: ignore[arg-type]
    service.reviews = SimpleNamespace(approved_story=lambda *_args, **_kwargs: None)
    with pytest.raises(ApprovedStoryRequired):
        service.load(project_id=uuid4())
