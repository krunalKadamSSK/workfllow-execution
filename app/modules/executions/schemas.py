from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StartWorkflowRequest(BaseModel):
    name: str
    workflow_definition_id: str
    version: int | None = None
    created_by: str | None = None


class SubmitNodeOutputsRequest(BaseModel):
    outputs: dict[str, Any] = Field(default_factory=dict)
    executed_by: str | None = None
    expected_revision: int | None = None


class WorkflowNodeInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_node_id: str
    node_definition_version_id: str
    status: str
    current_execution: int


class PendingNodeFormResponse(BaseModel):
    fields: list[dict[str, Any]] = Field(default_factory=list)


class ExecutionSummaryItem(BaseModel):
    workflow_node_id: str
    node_definition_id: str | None = None
    task_label: str | None = None
    output_key: str
    output_label: str
    value: Any = None


class ExecutionSummary(BaseModel):
    items: list[ExecutionSummaryItem] = Field(default_factory=list)
    total: float | None = None


class WorkflowInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    workflow_definition_id: str
    workflow_definition_version_id: str
    status: str
    current_revision: int
    created_at: datetime
    completed_at: datetime | None = None
    node_instances: list[WorkflowNodeInstanceResponse] = Field(default_factory=list)
    pending_node_ids: list[str] = Field(default_factory=list)
    next_task_id: str | None = None
    pending_node_forms: dict[str, PendingNodeFormResponse] = Field(default_factory=dict)
    workflow_projection: dict[str, Any] | None = None
    execution_summary: ExecutionSummary | None = None
    total_cost: float | None = None


class WorkflowEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence_number: int
    event_type: str
    payload_json: dict[str, Any]
    created_at: datetime
