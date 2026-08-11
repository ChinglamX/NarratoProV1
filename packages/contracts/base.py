"""Shared behavior for immutable, strictly validated public contracts."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict


class StrictContract(BaseModel):
    """Base class for public contracts with deterministic JSON serialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        """Return stable UTF-8 JSON suitable for hashing and replay keys."""

        value: Any = self.model_dump(mode="json", by_alias=True, exclude_none=False)
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def canonical_bytes(self) -> bytes:
        """Return the canonical JSON encoded as UTF-8."""

        return self.canonical_json().encode("utf-8")
