from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.infrastructure.db.models.definitions import WorkflowDefinition, WorkflowDefinitionVersion
from app.infrastructure.db.models.enums import ExecutionStatus, NodeStatus, WorkflowStatus


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    workflow_definition_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_definitions.id"),
        nullable=False,
    )
    workflow_definition_version_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_definition_versions.id"),
        nullable=False,
    )
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, name="workflow_status"),
        nullable=False,
    )
    current_revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow_definition: Mapped["WorkflowDefinition"] = relationship(back_populates="instances")
    workflow_definition_version: Mapped["WorkflowDefinitionVersion"] = relationship(
        back_populates="instances"
    )
    snapshot: Mapped["WorkflowSnapshot | None"] = relationship(
        back_populates="workflow_instance",
        uselist=False,
        cascade="all, delete-orphan",
    )
    node_instances: Mapped[list["WorkflowNodeInstance"]] = relationship(
        back_populates="workflow_instance",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["WorkflowEvent"]] = relationship(
        back_populates="workflow_instance",
        cascade="all, delete-orphan",
    )
    projection: Mapped["WorkflowProjection | None"] = relationship(
        back_populates="workflow_instance",
        uselist=False,
        cascade="all, delete-orphan",
    )


class WorkflowSnapshot(Base):
    __tablename__ = "workflow_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    workflow_instance_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workflow_instance: Mapped["WorkflowInstance"] = relationship(back_populates="snapshot")


class WorkflowNodeInstance(Base):
    __tablename__ = "workflow_node_instances"
    __table_args__ = (UniqueConstraint("workflow_instance_id", "workflow_node_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    workflow_instance_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_node_id: Mapped[str] = mapped_column(String, nullable=False)
    node_definition_version_id: Mapped[str] = mapped_column(
        ForeignKey("node_definition_versions.id"),
        nullable=False,
    )
    status: Mapped[NodeStatus] = mapped_column(
        Enum(NodeStatus, name="node_status"),
        nullable=False,
    )
    current_execution: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workflow_instance: Mapped["WorkflowInstance"] = relationship(back_populates="node_instances")
    executions: Mapped[list["WorkflowNodeExecution"]] = relationship(
        back_populates="workflow_node_instance",
        cascade="all, delete-orphan",
    )
    projection: Mapped["WorkflowNodeProjection | None"] = relationship(
        back_populates="workflow_node_instance",
        uselist=False,
        cascade="all, delete-orphan",
    )


class WorkflowNodeExecution(Base):
    __tablename__ = "workflow_node_executions"
    __table_args__ = (UniqueConstraint("workflow_node_instance_id", "execution_number"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    workflow_instance_id: Mapped[str] = mapped_column(String, nullable=False)
    workflow_node_instance_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_node_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_number: Mapped[int] = mapped_column(Integer, nullable=False)
    inputs_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    outputs_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, name="execution_status"),
        nullable=False,
    )
    executed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow_node_instance: Mapped["WorkflowNodeInstance"] = relationship(
        back_populates="executions"
    )
