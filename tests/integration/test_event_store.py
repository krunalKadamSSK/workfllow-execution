import pytest

from app.application.events.event_store import EventStore
from app.application.events.factory import create_default_event_handler_registry
from app.application.events.rebuilder import ProjectionRebuilder
from app.domain.enums import WorkflowStatus
from app.domain.events.types import WorkflowEventType
from app.infrastructure.db.repositories.definitions import DefinitionRepository
from app.infrastructure.db.repositories.events import EventRepository
from app.infrastructure.db.repositories.instances import InstanceRepository
from app.infrastructure.db.repositories.projections import ProjectionRepository

pytestmark = pytest.mark.integration


class TestEventStoreAndProjections:
    def _create_instance(self, db_session):
        definitions = DefinitionRepository(db_session)
        instances = InstanceRepository(db_session)

        workflow, workflow_version = definitions.create_workflow_definition(
            name="Event Workflow",
            slug="event-store-workflow",
            status="published",
            definition_json={"nodes": [], "edges": []},
        )
        node, node_version = definitions.create_node_definition(
            name="Task",
            slug="event-store-node",
            status="published",
            definition_json={"baseKind": "userInput", "form": {"fields": []}},
        )
        db_session.flush()

        instance = instances.create_workflow_instance(
            name="Run",
            workflow_definition_id=workflow.id,
            workflow_definition_version_id=workflow_version.id,
            status=WorkflowStatus.PENDING,
        )
        node_instance = instances.create_node_instance(
            workflow_instance_id=instance.id,
            workflow_node_id="graph-node-1",
            node_definition_version_id=node_version.id,
        )
        db_session.flush()
        return instance, node_instance, workflow, workflow_version

    def test_append_updates_workflow_and_node_projections(self, db_session):
        instance, node_instance, workflow, workflow_version = self._create_instance(db_session)
        projections = ProjectionRepository(db_session)
        instances = InstanceRepository(db_session)
        events = EventRepository(db_session)
        registry = create_default_event_handler_registry(
            projection_repository=projections,
            instance_repository=instances,
        )
        store = EventStore(events, registry, hash_chain_enabled=True)

        store.append(
            workflow_instance_id=instance.id,
            event_type=WorkflowEventType.WORKFLOW_STARTED.value,
            payload_json={
                "workflow_instance_id": instance.id,
                "workflow_definition_id": workflow.id,
                "workflow_definition_version_id": workflow_version.id,
                "snapshot_json": {"nodes": [], "edges": []},
            },
        )
        store.append(
            workflow_instance_id=instance.id,
            event_type=WorkflowEventType.NODE_COMPLETED.value,
            payload_json={
                "workflow_instance_id": instance.id,
                "workflow_node_instance_id": node_instance.id,
                "workflow_node_id": "graph-node-1",
                "execution_number": 1,
                "outputs": {"customerName": "ACME"},
            },
        )
        db_session.flush()

        workflow_state = projections.get_workflow_state(instance.id)
        assert workflow_state is not None
        assert workflow_state["status"] == "RUNNING"
        assert workflow_state["nodes"]["graph-node-1"]["outputs"]["customerName"] == "ACME"

        node_values = projections.get_node_values_by_graph_id(
            workflow_instance_id=instance.id,
            workflow_node_id="graph-node-1",
        )
        assert node_values == {"customerName": "ACME"}

        assert instances.get_snapshot(instance.id) is not None

        stored_events = events.list_events(instance.id)
        assert len(stored_events) == 2
        assert stored_events[0].current_hash is not None
        assert stored_events[1].previous_hash == stored_events[0].current_hash

    def test_projection_rebuild_replays_event_log(self, db_session):
        instance, node_instance, workflow, workflow_version = self._create_instance(db_session)
        projections = ProjectionRepository(db_session)
        instances = InstanceRepository(db_session)
        events = EventRepository(db_session)
        registry = create_default_event_handler_registry(
            projection_repository=projections,
            instance_repository=instances,
        )
        store = EventStore(events, registry)
        rebuilder = ProjectionRebuilder(
            event_repository=events,
            projection_repository=projections,
            handler_registry=registry,
        )

        store.append(
            workflow_instance_id=instance.id,
            event_type=WorkflowEventType.WORKFLOW_STARTED.value,
            payload_json={
                "workflow_instance_id": instance.id,
                "workflow_definition_id": workflow.id,
                "workflow_definition_version_id": workflow_version.id,
            },
        )
        store.append(
            workflow_instance_id=instance.id,
            event_type=WorkflowEventType.NODE_COMPLETED.value,
            payload_json={
                "workflow_instance_id": instance.id,
                "workflow_node_instance_id": node_instance.id,
                "workflow_node_id": "graph-node-1",
                "execution_number": 1,
                "outputs": {"partName": "PART-1"},
            },
        )
        db_session.flush()

        projections.delete_projections_for_instance(instance.id)
        db_session.flush()
        assert projections.get_workflow_state(instance.id) is None

        replayed = rebuilder.rebuild(instance.id)
        db_session.flush()

        assert replayed == 2
        rebuilt_state = projections.get_workflow_state(instance.id)
        assert rebuilt_state is not None
        assert rebuilt_state["nodes"]["graph-node-1"]["outputs"]["partName"] == "PART-1"
