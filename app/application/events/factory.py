from __future__ import annotations

from app.application.events.handlers.node_projection import WorkflowNodeProjectionHandler
from app.application.events.handlers.snapshot import WorkflowSnapshotHandler
from app.application.events.handlers.workflow_projection import WorkflowProjectionHandler
from app.application.events.registry import EventHandlerRegistry
from app.infrastructure.db.repositories.instances import InstanceRepository
from app.infrastructure.db.repositories.projections import ProjectionRepository


def create_default_event_handler_registry(
    *,
    projection_repository: ProjectionRepository,
    instance_repository: InstanceRepository,
) -> EventHandlerRegistry:
    registry = EventHandlerRegistry()
    registry.register(WorkflowProjectionHandler(projection_repository))
    registry.register(WorkflowNodeProjectionHandler(projection_repository))
    registry.register(WorkflowSnapshotHandler(instance_repository))
    return registry
