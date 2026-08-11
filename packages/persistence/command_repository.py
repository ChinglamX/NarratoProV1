"""Transactional command idempotency registration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, insert, select
from sqlalchemy.exc import IntegrityError

import packages.persistence.schema as schema


class IdempotencyConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CommandRecord:
    command_id: UUID
    idempotency_key: str
    request_checksum: str
    state: str
    response: dict[str, Any] | None


class CommandRepository:
    def register(
        self,
        connection: Connection,
        *,
        command_id: UUID,
        idempotency_key: str,
        command_type: str,
        project_id: UUID | None,
        request: dict[str, Any],
        request_checksum: str,
    ) -> CommandRecord:
        try:
            with connection.begin_nested():
                connection.execute(
                    insert(schema.command).values(
                        id=command_id,
                        idempotency_key=idempotency_key,
                        command_type=command_type,
                        project_id=project_id,
                        request_json=request,
                        request_checksum=request_checksum,
                        state="registered",
                    )
                )
            return CommandRecord(
                command_id=command_id,
                idempotency_key=idempotency_key,
                request_checksum=request_checksum,
                state="registered",
                response=None,
            )
        except IntegrityError as error:
            existing = (
                connection.execute(
                    select(schema.command).where(
                        schema.command.c.idempotency_key == idempotency_key
                    )
                )
                .mappings()
                .first()
            )
            if existing is None or existing["request_checksum"] != request_checksum:
                raise IdempotencyConflict(
                    "idempotency key was used for a different request"
                ) from error
            return CommandRecord(
                command_id=existing["id"],
                idempotency_key=existing["idempotency_key"],
                request_checksum=existing["request_checksum"],
                state=existing["state"],
                response=existing["response_json"],
            )
