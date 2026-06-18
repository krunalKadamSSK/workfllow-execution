import pytest

from app.domain.exceptions import DuplicateSlugError, SequenceConflictError, VersionConflictError
from app.infrastructure.db.models import NodeStatus, WorkflowStatus
from app.infrastructure.db.repositories.definitions import DefinitionRepository
from app.infrastructure.db.repositories.events import EventRepository
from app.infrastructure.db.repositories.instances import InstanceRepository
from app.infrastructure.db.repositories.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


class TestDefinitionRepository:
    def test_create_and_publish_node_definition(self, db_session):
        repo = DefinitionRepository(db_session)

        node, version = repo.create_node_definition(
            name="General information",
            slug="general-information",
            status="published",
            definition_json={"baseKind": "userInput", "form": {"fields": []}},
        )
        db_session.flush()

        assert node.latest_version == 1
        assert version.version == 1

        version_two = repo.publish_node_version(
            node_definition_id=node.id,
            definition_json={"baseKind": "userInput", "form": {"fields": [{"id": "x"}]}},
        )
        db_session.flush()

        assert node.latest_version == 2
        assert version_two.version == 2

    def test_duplicate_node_slug_raises(self, db_session):
        repo = DefinitionRepository(db_session)
        repo.create_node_definition(
            name="First",
            slug="duplicate-slug",
            status="published",
            definition_json={},
        )
        db_session.flush()

        with pytest.raises(DuplicateSlugError):
            repo.create_node_definition(
                name="Second",
                slug="duplicate-slug",
                status="published",
                definition_json={},
            )
            db_session.flush()

    def test_pin_workflow_version(self, db_session):
        repo = DefinitionRepository(db_session)
        workflow, version = repo.create_workflow_definition(
            name="Test Workflow",
            slug="test-workflow",
            status="published",
            definition_json={"nodes": [], "edges": []},
        )
        db_session.flush()

        pinned = repo.pin_workflow_version(workflow.id, version=1)
        assert pinned.id == version.id


class TestInstanceRepository:
    def test_create_workflow_instance_with_nodes(self, db_session):
        definitions = DefinitionRepository(db_session)
        instances = InstanceRepository(db_session)

        workflow, workflow_version = definitions.create_workflow_definition(
            name="Test Workflow",
            slug="wf-instance-test",
            status="published",
            definition_json={"nodes": [], "edges": []},
        )
        node, node_version = definitions.create_node_definition(
            name="Task",
            slug="task-node-instance-test",
            status="published",
            definition_json={"baseKind": "userInput"},
        )
        db_session.flush()

        instance = instances.create_workflow_instance(
            name="Run 1",
            workflow_definition_id=workflow.id,
            workflow_definition_version_id=workflow_version.id,
            status=WorkflowStatus.PENDING,
        )
        node_instance = instances.create_node_instance(
            workflow_instance_id=instance.id,
            workflow_node_id="graph-node-1",
            node_definition_version_id=node_version.id,
            status=NodeStatus.WAITING,
        )
        db_session.flush()

        assert instance.workflow_definition_version_id == workflow_version.id
        assert node_instance.workflow_node_id == "graph-node-1"

    def test_revision_conflict_raises(self, db_session):
        definitions = DefinitionRepository(db_session)
        instances = InstanceRepository(db_session)

        workflow, workflow_version = definitions.create_workflow_definition(
            name="Revision Workflow",
            slug="revision-workflow",
            status="published",
            definition_json={},
        )
        db_session.flush()

        instance = instances.create_workflow_instance(
            name="Run",
            workflow_definition_id=workflow.id,
            workflow_definition_version_id=workflow_version.id,
        )
        db_session.flush()

        with pytest.raises(VersionConflictError):
            instances.update_workflow_status(
                instance,
                WorkflowStatus.RUNNING,
                expected_revision=999,
            )


class TestEventRepository:
    def test_append_events_with_monotonic_sequence(self, db_session):
        definitions = DefinitionRepository(db_session)
        instances = InstanceRepository(db_session)
        events = EventRepository(db_session)

        workflow, workflow_version = definitions.create_workflow_definition(
            name="Event Workflow",
            slug="event-workflow",
            status="published",
            definition_json={},
        )
        db_session.flush()

        instance = instances.create_workflow_instance(
            name="Run",
            workflow_definition_id=workflow.id,
            workflow_definition_version_id=workflow_version.id,
        )
        db_session.flush()

        first = events.append_event(
            workflow_instance_id=instance.id,
            event_type="WORKFLOW_STARTED",
            payload_json={"instance_id": instance.id},
        )
        second = events.append_event(
            workflow_instance_id=instance.id,
            event_type="NODE_READY",
            payload_json={"node_id": "n1"},
        )
        db_session.flush()

        assert first.sequence_number == 1
        assert second.sequence_number == 2
        assert len(events.list_events(instance.id)) == 2

    def test_duplicate_sequence_raises(self, db_session):
        definitions = DefinitionRepository(db_session)
        instances = InstanceRepository(db_session)
        events = EventRepository(db_session)

        workflow, workflow_version = definitions.create_workflow_definition(
            name="Sequence Workflow",
            slug="sequence-workflow",
            status="published",
            definition_json={},
        )
        db_session.flush()

        instance = instances.create_workflow_instance(
            name="Run",
            workflow_definition_id=workflow.id,
            workflow_definition_version_id=workflow_version.id,
        )
        db_session.flush()

        events.append_event(
            workflow_instance_id=instance.id,
            event_type="WORKFLOW_STARTED",
            payload_json={},
            sequence_number=1,
        )
        db_session.flush()

        with pytest.raises(SequenceConflictError):
            events.append_event(
                workflow_instance_id=instance.id,
                event_type="DUPLICATE",
                payload_json={},
                sequence_number=1,
            )
            db_session.flush()


class TestUnitOfWork:
    def test_unit_of_work_wires_repositories(self, db_session):
        uow = UnitOfWork(session_factory=lambda: db_session)
        with uow:
            node, version = uow.definitions.create_node_definition(
                name="UoW Node",
                slug="uow-node",
                status="published",
                definition_json={"baseKind": "userInput"},
            )
            db_session.flush()
            assert node.id
            assert version.node_definition_id == node.id
