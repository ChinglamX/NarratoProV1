from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from apps.api.reviews import (
    get_approved_story,
    get_approved_strategy,
    get_approved_timeline,
    get_released_candidate,
)


class EmptyRepository:
    def approved_story(self, *_args, **_kwargs):
        return None

    def approved_strategy_ref(self, *_args, **_kwargs):
        return None

    def publication_ref(self, *_args, **_kwargs):
        return None


class Engine:
    class Context:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return None

    def connect(self):
        return self.Context()


def test_unapproved_story_fails_closed() -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(database_engine=Engine(), review_repository=EmptyRepository())
        )
    )
    with pytest.raises(HTTPException) as captured:
        get_approved_story(uuid4(), request)  # type: ignore[arg-type]
    assert captured.value.status_code == 404


def test_unapproved_strategy_fails_closed() -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(database_engine=Engine(), review_repository=EmptyRepository())
        )
    )
    with pytest.raises(HTTPException) as captured:
        get_approved_strategy(uuid4(), request)  # type: ignore[arg-type]
    assert captured.value.status_code == 404


def test_unreleased_candidate_fails_closed() -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(database_engine=Engine(), review_repository=EmptyRepository())
        )
    )
    with pytest.raises(HTTPException) as captured:
        get_released_candidate(uuid4(), request)  # type: ignore[arg-type]
    assert captured.value.status_code == 404


def test_unapproved_timeline_fails_closed() -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(database_engine=Engine(), review_repository=EmptyRepository())
        )
    )
    with pytest.raises(HTTPException) as captured:
        get_approved_timeline(uuid4(), request)  # type: ignore[arg-type]
    assert captured.value.status_code == 404
