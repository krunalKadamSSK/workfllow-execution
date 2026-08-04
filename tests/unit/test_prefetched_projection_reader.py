from app.domain.enums import NodeStatus
from app.infrastructure.executions.projection_reader import PrefetchedNodeProjectionReader


def test_prefetched_projection_reader_returns_completed_values_only():
    reader = PrefetchedNodeProjectionReader(
        values_by_graph_id={
            "task-1": {"customerName": "ACME"},
            "task-2": {"amount": 10},
        },
        statuses_by_graph_id={
            "task-1": NodeStatus.COMPLETED,
            "task-2": NodeStatus.PENDING,
        },
    )

    assert reader.get_node_values(
        workflow_instance_id="inst-1",
        workflow_node_id="task-1",
    ) == {"customerName": "ACME"}
    assert (
        reader.get_node_values(
            workflow_instance_id="inst-1",
            workflow_node_id="task-2",
        )
        is None
    )
