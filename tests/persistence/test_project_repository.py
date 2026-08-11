from uuid import uuid4

from packages.persistence.project_repository import ProjectRepository


class RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[object] = []

    def execute(self, statement: object) -> None:
        self.statements.append(statement)


def test_project_and_run_commands_emit_expected_writes() -> None:
    connection = RecordingConnection()
    repository = ProjectRepository()
    project_id, run_id = uuid4(), uuid4()
    repository.create_project(connection, project_id=project_id, name="project")  # type: ignore[arg-type]
    repository.create_run(  # type: ignore[arg-type]
        connection,
        run_id=run_id,
        project_id=project_id,
        workflow_id="workflow",
        automation_policy_snapshot={"level": "L1"},
        resource_profile_snapshot={"queue": "cpu"},
        trace_id="a" * 32,
    )
    assert len(connection.statements) == 3
