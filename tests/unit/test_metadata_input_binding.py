"""Unit tests for metadata input bindings."""

from app.application.executions.input_binder import GraphInputBinder
from app.domain.exceptions import InputResolutionError
from app.domain.graph.workflow_graph import GraphInputBinding, GraphNode
from app.domain.validation.input_wiring import validate_input_wiring
from app.modules.definitions.schemas.workflows import WorkflowDefinitionIngest
import pytest


class _NoopUpstream:
    def resolve(self, *, workflow_instance_id: str, source_node_id: str, output_key: str):
        raise AssertionError("upstream should not be called")


def test_graph_input_binding_parses_metadata():
    binding = GraphInputBinding.from_dict(
        {
            "inputKey": "rfqId",
            "source": {"kind": "metadata", "key": "rfqId"},
            "locked": True,
        }
    )
    assert binding.kind == "metadata"
    assert binding.metadata_key == "rfqId"
    assert binding.locked is True


def test_binder_resolves_metadata_key():
    binder = GraphInputBinder(_NoopUpstream())
    node = GraphNode(
        id="task-1",
        kind="task",
        node_definition_id="def-1",
        inputs=(
            GraphInputBinding(
                input_key="rfqId",
                kind="metadata",
                metadata_key="rfqId",
                locked=True,
            ),
        ),
    )
    resolved = binder.resolve(
        workflow_instance_id="inst-1",
        graph_node=node,
        instance_metadata={"rfqId": "RFQ-1", "estimateRevision": "1"},
    )
    assert resolved.values == {"rfqId": "RFQ-1"}
    assert resolved.locked_keys == frozenset({"rfqId"})


def test_binder_missing_metadata_key_raises():
    binder = GraphInputBinder(_NoopUpstream())
    node = GraphNode(
        id="task-1",
        kind="task",
        node_definition_id="def-1",
        inputs=(
            GraphInputBinding(
                input_key="plantCode",
                kind="metadata",
                metadata_key="plantCode",
            ),
        ),
    )
    with pytest.raises(InputResolutionError):
        binder.resolve(
            workflow_instance_id="inst-1",
            graph_node=node,
            instance_metadata={"rfqId": "RFQ-1"},
        )


def test_validate_metadata_binding_allows_system_and_declared_keys():
    workflow = WorkflowDefinitionIngest.model_validate(
        {
            "id": "wf-1",
            "name": "Meta workflow",
            "slug": "meta-workflow",
            "status": "draft",
            "version": "1",
            "metadataFields": [
                {"key": "plantCode", "label": "Plant", "type": "text", "required": True}
            ],
            "nodes": [
                {"id": "start-1", "kind": "start", "position": {"x": 0, "y": 0}},
                {
                    "id": "task-1",
                    "kind": "task",
                    "nodeDefinitionId": "node-def-1",
                    "position": {"x": 100, "y": 0},
                    "inputs": [
                        {
                            "inputKey": "rfqId",
                            "source": {"kind": "metadata", "key": "rfqId"},
                            "locked": True,
                        },
                        {
                            "inputKey": "plant",
                            "source": {"kind": "metadata", "key": "plantCode"},
                        },
                    ],
                },
                {"id": "end-1", "kind": "end", "position": {"x": 200, "y": 0}},
            ],
            "edges": [
                {"id": "e1", "source": "start-1", "target": "task-1"},
                {"id": "e2", "source": "task-1", "target": "end-1"},
            ],
        }
    )
    issues = validate_input_wiring(
        workflow,
        node_output_fields={"node-def-1": {"rfqId", "plant"}},
        node_input_fields={"node-def-1": {"rfqId", "plant"}},
    )
    assert issues == []


def test_validate_metadata_binding_rejects_unknown_key():
    workflow = WorkflowDefinitionIngest.model_validate(
        {
            "id": "wf-1",
            "name": "Meta workflow",
            "slug": "meta-workflow",
            "status": "draft",
            "version": "1",
            "nodes": [
                {"id": "start-1", "kind": "start", "position": {"x": 0, "y": 0}},
                {
                    "id": "task-1",
                    "kind": "task",
                    "nodeDefinitionId": "node-def-1",
                    "position": {"x": 100, "y": 0},
                    "inputs": [
                        {
                            "inputKey": "x",
                            "source": {"kind": "metadata", "key": "unknownKey"},
                        }
                    ],
                },
                {"id": "end-1", "kind": "end", "position": {"x": 200, "y": 0}},
            ],
            "edges": [
                {"id": "e1", "source": "start-1", "target": "task-1"},
                {"id": "e2", "source": "task-1", "target": "end-1"},
            ],
        }
    )
    issues = validate_input_wiring(
        workflow,
        node_output_fields={"node-def-1": {"x"}},
        node_input_fields={"node-def-1": {"x"}},
    )
    assert any(issue.code == "UNKNOWN_METADATA_KEY" for issue in issues)
