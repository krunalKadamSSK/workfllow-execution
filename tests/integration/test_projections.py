import pytest

from app.infrastructure.db.repositories.projections import ProjectionRepository
from app.infrastructure.executions.projection_reader import DbNodeProjectionReader

pytestmark = pytest.mark.integration


class TestProjectionRepository:
    def test_upsert_and_read_node_projection(self, db_session):
        from app.infrastructure.db.models import NodeStatus, WorkflowStatus
        from app.infrastructure.db.repositories.definitions import DefinitionRepository
        from app.infrastructure.db.repositories.instances import InstanceRepository

        definitions = DefinitionRepository(db_session)
        instances = InstanceRepository(db_session)
        projections = ProjectionRepository(db_session)

        workflow, workflow_version = definitions.create_workflow_definition(
            name="Projection Workflow",
            slug="projection-workflow",
            status="published",
            definition_json={},
        )
        node, node_version = definitions.create_node_definition(
            name="Task",
            slug="projection-node",
            status="published",
            definition_json={"baseKind": "userInput", "form": {"fields": []}},
        )
        db_session.flush()

        instance = instances.create_workflow_instance(
            name="Run",
            workflow_definition_id=workflow.id,
            workflow_definition_version_id=workflow_version.id,
            status=WorkflowStatus.RUNNING,
        )
        node_instance = instances.create_node_instance(
            workflow_instance_id=instance.id,
            workflow_node_id="graph-node-1",
            node_definition_version_id=node_version.id,
            status=NodeStatus.COMPLETED,
        )
        db_session.flush()

        projections.upsert_node_projection(
            workflow_instance_id=instance.id,
            workflow_node_instance_id=node_instance.id,
            current_values_json={"customerName": "ACME"},
        )
        db_session.flush()

        reader = DbNodeProjectionReader(projections)
        values = reader.get_node_values(
            workflow_instance_id=instance.id,
            workflow_node_id="graph-node-1",
        )
        assert values == {"customerName": "ACME"}
