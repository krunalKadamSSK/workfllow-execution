"""Port: workflow instance persistence."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.domain.enums import ExecutionStatus, NodeStatus, WorkflowStatus


@runtime_checkable
class InstanceRepositoryPort(Protocol):
    def create_workflow_instance(
        self,
        *,
        name: str,
        workflow_definition_id: str,
        workflow_definition_version_id: str,
        status: WorkflowStatus = ...,
        created_by: str | None = None,
        instance_id: str | None = None,
        metadata: Any = None,
        seed_defaults: dict | None = None,
    ) -> Any: ...

    def create_snapshot(self, *, workflow_instance_id: str, snapshot_json: dict) -> Any: ...

    def create_node_instance(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        node_definition_version_id: str,
        status: NodeStatus = ...,
        node_instance_id: str | None = None,
    ) -> Any: ...

    def get_workflow_instance(self, instance_id: str) -> Any | None: ...

    def require_workflow_instance(self, instance_id: str) -> Any: ...

    def list_node_instances(self, workflow_instance_id: str) -> list[Any]: ...

    def require_node_instance_by_graph_id(
        self, workflow_instance_id: str, workflow_node_id: str
    ) -> Any: ...

    def update_node_status(self, node_instance: Any, status: NodeStatus) -> Any: ...

    def create_node_execution(
        self,
        *,
        workflow_instance_id: str,
        node_instance: Any,
        inputs_json: dict,
        outputs_json: dict,
        status: ExecutionStatus,
        executed_by: str | None = None,
    ) -> Any: ...

    def update_workflow_status(
        self,
        instance: Any,
        status: WorkflowStatus,
        *,
        expected_revision: int | None = None,
    ) -> Any: ...

    def increment_revision(
        self, instance: Any, *, expected_revision: int | None = None
    ) -> Any: ...

    def get_snapshot(self, workflow_instance_id: str) -> Any | None: ...

    def list_workflow_instances(self) -> list[Any]: ...

    def list_by_rfq_id(
        self, rfq_id: str, *, incomplete_only: bool = False
    ) -> list[Any]: ...

    def list_by_rfq_id_page(
        self,
        rfq_id: str,
        page: Any,
        *,
        incomplete_only: bool = False,
        status: WorkflowStatus | None = None,
        created_from: Any = None,
        created_to: Any = None,
    ) -> Any: ...

    def has_incomplete_for_rfq(self, rfq_id: str) -> bool: ...

    def list_node_executions(self, workflow_instance_id: str) -> list[Any]: ...

    def list_node_execution_rows(
        self,
        workflow_instance_id: str,
        *,
        workflow_node_id: str | None = None,
        status: ExecutionStatus | None = None,
    ) -> list[Any]: ...

    def list_node_executions_page(
        self,
        workflow_instance_id: str,
        page: Any,
        *,
        workflow_node_id: str | None = None,
        status: ExecutionStatus | None = None,
    ) -> Any: ...

    def list_all_node_instances(self) -> list[Any]: ...

    def list_all_node_executions(self) -> list[Any]: ...
