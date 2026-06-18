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
    workflow_projection: dict[str, Any] | None = None


class WorkflowEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence_number: int
    event_type: str
    payload_json: dict[str, Any]
    created_at: datetime
