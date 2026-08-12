from contextlib import contextmanager
from types import MethodType, SimpleNamespace
from uuid import uuid4

from apps.services.provider_invocation import ProviderInvocationService
from packages.contracts import ArtifactRef
from packages.providers import ProviderRawOutput
from tests.providers.test_gateway import FakeProvider, package, policy, request


def test_provider_invocation_service_records_raw_artifact(monkeypatch, tmp_path) -> None:
    from packages.artifacts import LocalObjectStore

    service = ProviderInvocationService(engine=object(), object_store=LocalObjectStore(tmp_path))  # type: ignore[arg-type]
    artifact_id = uuid4()
    project_id, run_id = uuid4(), uuid4()

    class FakeConnect:
        def __enter__(self):
            return SimpleNamespace(execute=lambda *_a, **_k: SimpleNamespace(first=lambda: None))

        def __exit__(self, *_args):
            return None

    service.engine = SimpleNamespace(connect=lambda: FakeConnect())  # type: ignore[assignment]

    @contextmanager
    def fake_transaction(_engine):
        yield object()

    monkeypatch.setattr("apps.services.provider_invocation.transaction", fake_transaction)
    blob_id = uuid4()
    service.blobs.register_or_get_staged = MethodType(  # type: ignore[method-assign]
        lambda _self, _connection, metadata, **_kwargs: SimpleNamespace(
            state="committed", blob_id=blob_id, metadata=metadata
        ),
        service.blobs,
    )
    service.artifacts.reserve = MethodType(lambda *_a, **_k: None, service.artifacts)  # type: ignore[method-assign]
    service.artifacts.commit_version = MethodType(  # type: ignore[method-assign]
        lambda _self, _connection, envelope, **_kwargs: envelope.as_ref(), service.artifacts
    )
    provider = FakeProvider(package())
    provider.infer = lambda _request: ProviderRawOutput(  # type: ignore[method-assign]
        b'{"text":"hello"}', "application/json", "1", 2, 0
    )
    reference, admitted = service.invoke_and_record(
        provider=provider,
        request=request(),
        policy=policy(),
        raw_artifact_id=artifact_id,
        project_id=project_id,
        run_id=run_id,
        trace_id="a" * 32,
        rights_class="internal-observation",
    )
    assert reference == ArtifactRef(
        artifact_id=artifact_id,
        version=1,
        artifact_type="RawProviderResponse",
        checksum="sha256:" + __import__("hashlib").sha256(b'{"text":"hello"}').hexdigest(),
    )
    assert admitted.admission == "production"
