from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from apps.api import media


def test_media_catalog_api_requires_read_role() -> None:
    with pytest.raises(HTTPException) as captured:
        media.get_media_catalog(uuid4(), SimpleNamespace(), "publisher")
    assert captured.value.status_code == 403


class FakeConnection:
    def __init__(self, values: list[object]) -> None:
        self.values = iter(values)

    def scalar(self, _statement: object) -> object:
        return next(self.values)


class FakeConnect:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def __enter__(self) -> FakeConnection:
        return self.connection

    def __exit__(self, *_args: object) -> None:
        return None


def test_media_catalog_api_returns_active_contract() -> None:
    catalog_id = uuid4()
    source_id = uuid4()
    connection = FakeConnection(
        [
            1,
            {
                "source": {
                    "artifact_id": str(source_id),
                    "version": 1,
                    "artifact_type": "SourceMedia",
                },
                "segments": [],
            },
        ]
    )
    engine = SimpleNamespace(connect=lambda: FakeConnect(connection))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database_engine=engine)))
    result = media.get_media_catalog(catalog_id, request, "viewer")  # type: ignore[arg-type]
    assert result.source.artifact_id == source_id


def test_media_catalog_api_returns_not_found() -> None:
    connection = FakeConnection([None])
    engine = SimpleNamespace(connect=lambda: FakeConnect(connection))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database_engine=engine)))
    with pytest.raises(HTTPException) as captured:
        media.get_media_catalog(uuid4(), request, "reviewer", version=1)  # type: ignore[arg-type]
    assert captured.value.status_code == 404
