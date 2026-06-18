from app.domain.enums import WorkflowStatus
from app.domain.exceptions import InvalidTransitionError


class WorkflowStateMachine:
    """State pattern for workflow instance lifecycle transitions."""

    _TRANSITIONS: dict[WorkflowStatus, frozenset[WorkflowStatus]] = {
        WorkflowStatus.PENDING: frozenset({WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED}),
        WorkflowStatus.RUNNING: frozenset(
            {
                WorkflowStatus.PAUSED,
                WorkflowStatus.COMPLETED,
                WorkflowStatus.CANCELLED,
            }
        ),
        WorkflowStatus.PAUSED: frozenset({WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED}),
        WorkflowStatus.COMPLETED: frozenset(),
        WorkflowStatus.CANCELLED: frozenset(),
    }

    def can_transition(self, current: WorkflowStatus, target: WorkflowStatus) -> bool:
        if current == target:
            return True
        return target in self._TRANSITIONS.get(current, frozenset())

    def transition(self, current: WorkflowStatus, target: WorkflowStatus) -> WorkflowStatus:
        if not self.can_transition(current, target):
            raise InvalidTransitionError(
                f"Illegal workflow transition from {current.value} to {target.value}"
            )
        return target

    def allowed_targets(self, current: WorkflowStatus) -> frozenset[WorkflowStatus]:
        return self._TRANSITIONS.get(current, frozenset())

    def is_terminal(self, status: WorkflowStatus) -> bool:
        return not self._TRANSITIONS.get(status, frozenset())
