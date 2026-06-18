from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass(frozen=True)
class WorkflowStartedPayload:
    workflow_instance_id: str
    workflow_definition_id: str
    workflow_definition_version_id: str
    snapshot_json: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "workflow_instance_id": self.workflow_instance_id,
            "workflow_definition_id": self.workflow_definition_id,
            "workflow_definition_version_id": self.workflow_definition_version_id,
        }
        if self.snapshot_json is not None:
            payload["snapshot_json"] = self.snapshot_json
        return payload


@dataclasses.dataclass(frozen=True)
class WorkflowStatusChangedPayload:
    workflow_instance_id: str
    from_status: str
    to_status: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class NodeReadyPayload:
    workflow_instance_id: str
    workflow_node_instance_id: str
    workflow_node_id: str
    node_definition_version_id: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class NodeStartedPayload:
    workflow_instance_id: str
    workflow_node_instance_id: str
    workflow_node_id: str
    execution_number: int

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class NodeCompletedPayload:
    workflow_instance_id: str
    workflow_node_instance_id: str
    workflow_node_id: str
    execution_number: int
    outputs: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_instance_id": self.workflow_instance_id,
            "workflow_node_instance_id": self.workflow_node_instance_id,
            "workflow_node_id": self.workflow_node_id,
            "execution_number": self.execution_number,
            "outputs": self.outputs,
        }


@dataclasses.dataclass(frozen=True)
class NodeFailedPayload:
    workflow_instance_id: str
    workflow_node_instance_id: str
    workflow_node_id: str
    execution_number: int
    error_message: str
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = dataclasses.asdict(self)
        if payload["error_code"] is None:
            payload.pop("error_code")
        return payload


@dataclasses.dataclass(frozen=True)
class NodeInvalidatedPayload:
    workflow_instance_id: str
    workflow_node_instance_id: str
    workflow_node_id: str
    reason: str
    upstream_node_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = dataclasses.asdict(self)
        if payload["upstream_node_id"] is None:
            payload.pop("upstream_node_id")
        return payload
