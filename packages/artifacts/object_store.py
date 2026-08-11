"""Object-store port and atomic local filesystem adapter."""

from __future__ import annotations

import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BlobMetadata:
    uri: str
    checksum: str
    size_bytes: int


class ObjectStore(Protocol):
    def stage(self, run_id: UUID, activity_id: str, source: BinaryIO) -> BlobMetadata: ...

    def commit(self, staged_uri: str, expected_checksum: str) -> BlobMetadata: ...

    def open(self, uri: str) -> BinaryIO: ...

    def head(self, uri: str) -> BlobMetadata: ...

    def delete_staged(self, uri: str) -> None: ...


class ObjectStoreError(RuntimeError):
    pass


class ChecksumMismatch(ObjectStoreError):
    pass


class InvalidObjectUri(ObjectStoreError):
    pass


class LocalObjectStore:
    """Content-addressed store using same-filesystem atomic rename."""

    URI_SCHEME = "local-object://"

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._staging = self._root / "staging"
        self._objects = self._root / "objects" / "sha256"
        self._staging.mkdir(parents=True, exist_ok=True)
        self._objects.mkdir(parents=True, exist_ok=True)

    def _path_for_uri(self, uri: str) -> Path:
        if not uri.startswith(self.URI_SCHEME):
            raise InvalidObjectUri("unsupported object URI scheme")
        relative = uri.removeprefix(self.URI_SCHEME)
        if not relative or relative.startswith("/"):
            raise InvalidObjectUri("object URI must be a relative store key")
        path = (self._root / relative).resolve()
        if path != self._root and self._root not in path.parents:
            raise InvalidObjectUri("object URI escapes store root")
        return path

    def _uri_for_path(self, path: Path) -> str:
        return self.URI_SCHEME + path.relative_to(self._root).as_posix()

    def stage(self, run_id: UUID, activity_id: str, source: BinaryIO) -> BlobMetadata:
        if not activity_id or any(
            character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
            for character in activity_id
        ):
            raise InvalidObjectUri("activity_id contains unsafe characters")
        directory = self._staging / str(run_id)
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{activity_id}.part"
        temporary = directory / f".{activity_id}.{os.getpid()}.tmp"
        digest = sha256()
        size = 0
        try:
            with temporary.open("xb") as output:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return BlobMetadata(
            uri=self._uri_for_path(target),
            checksum=f"sha256:{digest.hexdigest()}",
            size_bytes=size,
        )

    def commit(self, staged_uri: str, expected_checksum: str) -> BlobMetadata:
        staged = self._path_for_uri(staged_uri)
        expected_prefix = "sha256:"
        if not expected_checksum.startswith(expected_prefix) or len(expected_checksum) != 71:
            raise ChecksumMismatch("expected checksum must use sha256:<digest>")
        actual = self.head(staged_uri)
        if actual.checksum != expected_checksum:
            raise ChecksumMismatch("staged blob checksum does not match expected checksum")
        digest = expected_checksum.removeprefix(expected_prefix)
        target = self._objects / digest[:2] / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            existing = self._metadata(target)
            if existing.checksum != expected_checksum or existing.size_bytes != actual.size_bytes:
                raise ChecksumMismatch("content-addressed target does not match staged blob")
            staged.unlink()
            return existing
        os.replace(staged, target)
        return self._metadata(target)

    def _metadata(self, path: Path) -> BlobMetadata:
        digest = sha256()
        size = 0
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
        return BlobMetadata(
            uri=self._uri_for_path(path),
            checksum=f"sha256:{digest.hexdigest()}",
            size_bytes=size,
        )

    def open(self, uri: str) -> BinaryIO:
        return self._path_for_uri(uri).open("rb")

    def head(self, uri: str) -> BlobMetadata:
        path = self._path_for_uri(uri)
        if not path.is_file():
            raise FileNotFoundError(uri)
        return self._metadata(path)

    def delete_staged(self, uri: str) -> None:
        path = self._path_for_uri(uri)
        try:
            path.relative_to(self._staging)
        except ValueError as error:
            raise InvalidObjectUri("only staged objects may be deleted") from error
        path.unlink(missing_ok=True)
