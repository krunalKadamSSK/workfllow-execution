"""Wire ExecutionService collaborators from a SQLAlchemy session."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.events.event_store import EventStore
from app.application.events.factory import create_default_event_handler_registry
from app.application.executions.auto_node_runner import AutoNodeRunner
from app.application.executions.commands.control import ControlWorkflowCommand
from app.application.executions.commands.start import StartWorkflowCommand
from app.application.executions.commands.submit import SubmitNodeOutputsCommand
from app.application.executions.graph_runtime import GraphRuntime
from app.application.executions.queries.export import ExportInstancesQuery
from app.application.executions.queries.get_instance import GetInstanceStateQuery
from app.application.executions.queries.list_instances import ListInstancesQuery
from app.application.executions.queries.node_execution_logs import NodeExecutionLogQuery
from app.core.config import settings
from app.infrastructure.persistence.repositories.definitions import DefinitionRepository
from app.infrastructure.persistence.repositories.events import EventRepository
from app.infrastructure.persistence.repositories.instances import InstanceRepository
from app.infrastructure.persistence.repositories.projections import ProjectionRepository
from app.patterns.executions.factories import create_default_registry


class ExecutionServiceFactory:
    """Builds a fully wired ``ExecutionService`` for a request session."""

    @staticmethod
    def create(session: Session):
        from app.application.executions.service import ExecutionService

        definitions = DefinitionRepository(session)
        instances = InstanceRepository(session)
        events = EventRepository(session)
        projections = ProjectionRepository(session)
        handler_registry = create_default_event_handler_registry(
            projection_repository=projections,
            instance_repository=instances,
        )
        event_store = EventStore(
            events,
            handler_registry,
            hash_chain_enabled=settings.EVENT_HASH_CHAIN,
        )
        executors = create_default_registry()
        auto_runner = AutoNodeRunner(
            definitions=definitions,
            instances=instances,
            projections=projections,
            events=event_store,
            executors=executors,
        )
        runtime = GraphRuntime(
            definition_repository=definitions,
            instance_repository=instances,
            event_store=event_store,
            auto_runner=auto_runner,
        )
        get_instance = GetInstanceStateQuery(
            definitions=definitions,
            instances=instances,
            projections=projections,
            executors=executors,
            runtime=runtime,
        )
        return ExecutionService(
            session=session,
            start=StartWorkflowCommand(
                definitions=definitions,
                instances=instances,
                events=event_store,
                runtime=runtime,
            ),
            submit=SubmitNodeOutputsCommand(
                definitions=definitions,
                instances=instances,
                projections=projections,
                events=event_store,
                executors=executors,
                runtime=runtime,
            ),
            control=ControlWorkflowCommand(
                instances=instances,
                events=event_store,
                runtime=runtime,
            ),
            list_instances=ListInstancesQuery(instances=instances),
            get_instance=get_instance,
            export=ExportInstancesQuery(
                definitions=definitions,
                instances=instances,
                projections=projections,
                events=event_store,
                get_instance=get_instance,
                load_graph=runtime.load_graph,
            ),
            node_execution_logs=NodeExecutionLogQuery(
                instances=instances,
                definitions=definitions,
                load_graph=runtime.load_graph,
            ),
            event_repository=events,
        )
