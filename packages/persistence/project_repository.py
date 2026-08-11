"""Project/run command persistence with transactional workflow-start outbox."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, insert

import packages.persistence.schema as schema


class ProjectRepository:
    def create_project(self, connection: Connection, *, project_id: UUID, name: str) -> None:
        connection.execute(insert(schema.project).values(id=project_id, name=name, state="active"))

    def create_run(
        self,
        connection: Connection,
        *,
        run_id: UUID,
        project_id: UUID,
        workflow_id: str,
        automation_policy_snapshot: dict[str, Any],
        resource_profile_snapshot: dict[str, Any],
        trace_id: str,
    ) -> None:
        connection.execute(
            insert(schema.run).values(
                id=run_id,
                project_id=project_id,
                workflow_id=workflow_id,
                state="start_pending",
                automation_policy_snapshot=automation_policy_snapshot,
                resource_profile_snapshot=resource_profile_snapshot,
            )
        )
        connection.execute(
            insert(schema.outbox_event).values(
                id=uuid4(),
                aggregate_id=str(run_id),
                event_type="workflow.start.requested",
                payload_json={
                    "workflow_id": workflow_id,
                    "run_id": str(run_id),
                    "project_id": str(project_id),
                    "automation_policy": automation_policy_snapshot,
                    "resource_profile": resource_profile_snapshot,
                },
                trace_id=trace_id,
            )
        )
