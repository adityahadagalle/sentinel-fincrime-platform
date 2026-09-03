"""
AuditEvent ORM Model for SENTINEL (Phase 7).
"""

from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Dialect-compatible JSON type
JSONType = JSONB().with_variant(JSON(), "sqlite")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="CASE_DISPOSITION_MUTATION"
    )
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cases.case_id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    primary_tx_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("transactions.tx_id", ondelete="RESTRICT"),
        nullable=False
    )
    analyst_id: Mapped[str] = mapped_column(String(64), nullable=False)
    analyst_role: Mapped[str] = mapped_column(String(64), nullable=False)
    action_code: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_case_status: Mapped[str] = mapped_column(String(32), nullable=False)
    new_case_status: Mapped[str] = mapped_column(String(32), nullable=False)
    analyst_notes: Mapped[str] = mapped_column(Text, nullable=False)
    risk_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    decision_support_summary: Mapped[dict] = mapped_column(JSONType, nullable=False)
    traceability_chain: Mapped[dict] = mapped_column(JSONType, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_audit_events_case_time", "case_id", timestamp.desc()),
    )

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="audit_events"
    )
    transaction: Mapped["Transaction"] = relationship("Transaction")
