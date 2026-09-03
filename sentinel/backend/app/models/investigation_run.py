"""
InvestigationRun ORM Model for SENTINEL (Phase 9 Reliability Hardening).
"""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Dialect-compatible JSON type
JSONType = JSONB().with_variant(JSON(), "sqlite")


class InvestigationRun(Base):
    __tablename__ = "investigation_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cases.case_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING", index=True)
    current_stage: Mapped[str] = mapped_column(String(32), nullable=False, default="NONE")
    stage_states: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    summary: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    force_rerun: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_inv_runs_case_status", "case_id", "status"),
    )

    # Relationship
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="investigation_runs"
    )
