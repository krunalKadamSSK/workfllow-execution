from app.domain.enums import NodeStatus
from app.domain.exceptions import InvalidTransitionError


class NodeStateMachine:
    """State pattern for workflow node instance lifecycle transitions."""

    _TRANSITIONS: dict[NodeStatus, frozenset[NodeStatus]] = {
        NodeStatus.WAITING: frozenset({NodeStatus.PENDING, NodeStatus.INVALIDATED}),
        NodeStatus.PENDING: frozenset(
            {
                NodeStatus.RUNNING,
                NodeStatus.INVALIDATED,
                NodeStatus.FAILED,
            }
        ),
        NodeStatus.RUNNING: frozenset(
            {
                NodeStatus.COMPLETED,
                NodeStatus.FAILED,
                NodeStatus.INVALIDATED,
            }
        ),
        NodeStatus.COMPLETED: frozenset({NodeStatus.INVALIDATED, NodeStatus.PENDING}),
        NodeStatus.INVALIDATED: frozenset({NodeStatus.PENDING, NodeStatus.WAITING}),
        NodeStatus.FAILED: frozenset({NodeStatus.PENDING, NodeStatus.INVALIDATED}),
    }

    def can_transition(self, current: NodeStatus, target: NodeStatus) -> bool:
        if current == target:
            return True
        return target in self._TRANSITIONS.get(current, frozenset())

    def transition(self, current: NodeStatus, target: NodeStatus) -> NodeStatus:
        if not self.can_transition(current, target):
            raise InvalidTransitionError(
                f"Illegal node transition from {current.value} to {target.value}"
            )
        return target

    def allowed_targets(self, current: NodeStatus) -> frozenset[NodeStatus]:
        return self._TRANSITIONS.get(current, frozenset())

    def is_terminal(self, status: NodeStatus) -> bool:
        return status in {NodeStatus.COMPLETED, NodeStatus.FAILED}
