"""Narration source boundary for E09 J03.

No narration-generation provider is production-admitted, so the L1 source is a
*human-approved* committed ``NarrationLineSet`` artifact. This module defines
the port only; adapters (e.g. the persistence-backed source in
``apps.services.narration_source``) never fabricate narration text and never
own selection policy.
"""

from __future__ import annotations

from typing import Protocol

from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import NarrationLineSet


class NarrationSourceUnavailable(RuntimeError):
    pass


class NarrationSourcePort(Protocol):
    def load(self, line_set_ref: ArtifactRef) -> NarrationLineSet: ...
