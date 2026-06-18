from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float
    y: float


class UpstreamSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["upstream"]
    sourceNodeId: str
    outputKey: str


class NodeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inputKey: str
    source: UpstreamSource
    locked: bool = False


class WorkflowNode(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    kind: Literal["start", "task", "end"]
    position: Position
    nodeDefinitionId: str | None = None
    label: str | None = None
    inputs: list[NodeInput] | None = None

    @model_validator(mode="after")
    def validate_kind_requirements(self) -> "WorkflowNode":
        if self.kind == "task" and not self.nodeDefinitionId:
            raise ValueError("Task nodes must include nodeDefinitionId")
        if self.kind in {"start", "end"} and self.nodeDefinitionId:
            raise ValueError(f"{self.kind} nodes must not include nodeDefinitionId")
        return self


class WorkflowEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    target: str


class WorkflowDefinitionJson(BaseModel):
    """JSON blob stored in workflow_definition_versions.definition_json."""

    model_config = ConfigDict(extra="forbid")

    description: str | None = None
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]


class WorkflowDefinitionIngest(BaseModel):
    """Full publish payload from the React Flow frontend."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    slug: str | None = None
    status: str
    version: str | int
    description: str | None = None
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_slug(self) -> "WorkflowDefinitionIngest":
        if not self.slug or not self.slug.strip():
            raise ValueError("Workflow slug is required")
        return self

    def to_stored_json(self) -> dict:
        return WorkflowDefinitionJson(
            description=self.description,
            nodes=self.nodes,
            edges=self.edges,
        ).model_dump()

    def task_nodes(self) -> list[WorkflowNode]:
        return [node for node in self.nodes if node.kind == "task"]
