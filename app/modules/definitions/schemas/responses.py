from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NodeDefinitionVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: int
    definition_json: dict[str, Any]
    created_by: str | None
    created_at: datetime


class NodeDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    status: str
    latest_version: int
    created_at: datetime
    updated_at: datetime
    version: NodeDefinitionVersionResponse | None = None


class WorkflowDefinitionVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: int
    definition_json: dict[str, Any]
    created_by: str | None
    created_at: datetime


class WorkflowDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    status: str
    latest_version: int
    created_at: datetime
    updated_at: datetime
    version: WorkflowDefinitionVersionResponse | None = None
