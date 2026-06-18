from pathlib import Path

import pytest

from app.domain.enums import NodeStatus, WorkflowStatus
from app.domain.exceptions import InvalidTransitionError
from app.domain.state.node import NodeStateMachine
from app.domain.state.workflow import WorkflowStateMachine

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestWorkflowStateMachine:
    def setup_method(self) -> None:
        self.sm = WorkflowStateMachine()

    def test_pending_to_running(self):
        assert self.sm.transition(WorkflowStatus.PENDING, WorkflowStatus.RUNNING) == (
            WorkflowStatus.RUNNING
        )

    def test_running_to_completed(self):
        assert self.sm.transition(WorkflowStatus.RUNNING, WorkflowStatus.COMPLETED) == (
            WorkflowStatus.COMPLETED
        )

    def test_completed_is_terminal(self):
        assert self.sm.is_terminal(WorkflowStatus.COMPLETED)
        assert not self.sm.can_transition(WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING)

    def test_illegal_transition_raises(self):
        with pytest.raises(InvalidTransitionError):
            self.sm.transition(WorkflowStatus.PENDING, WorkflowStatus.COMPLETED)

    def test_same_state_allowed(self):
        assert self.sm.can_transition(WorkflowStatus.RUNNING, WorkflowStatus.RUNNING)


class TestNodeStateMachine:
    def setup_method(self) -> None:
        self.sm = NodeStateMachine()

    def test_waiting_to_pending(self):
        assert self.sm.transition(NodeStatus.WAITING, NodeStatus.PENDING) == NodeStatus.PENDING

    def test_running_to_completed(self):
        assert self.sm.transition(NodeStatus.RUNNING, NodeStatus.COMPLETED) == NodeStatus.COMPLETED

    def test_completed_can_be_invalidated_for_rerun(self):
        assert self.sm.transition(NodeStatus.COMPLETED, NodeStatus.INVALIDATED) == (
            NodeStatus.INVALIDATED
        )

    def test_invalidated_can_return_to_pending(self):
        assert self.sm.transition(NodeStatus.INVALIDATED, NodeStatus.PENDING) == NodeStatus.PENDING

    def test_illegal_waiting_to_completed_raises(self):
        with pytest.raises(InvalidTransitionError):
            self.sm.transition(NodeStatus.WAITING, NodeStatus.COMPLETED)
