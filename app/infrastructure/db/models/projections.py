from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.instances import WorkflowInstance, WorkflowNodeInstance


class WorkflowProjection(Base):
    __tablename__ = "workflow_projections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    workflow_instance_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    current_state_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workflow_instance: Mapped[WorkflowInstance] = relationship(back_populates="projection")


class WorkflowNodeProjection(Base):
    __tablename__ = "workflow_node_projections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    workflow_instance_id: Mapped[str] = mapped_column(String, nullable=False)
    workflow_node_instance_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_node_instances.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    current_values_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workflow_node_instance: Mapped[WorkflowNodeInstance] = relationship(back_populates="projection")
