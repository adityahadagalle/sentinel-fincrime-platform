"""
Case ORM Model for SENTINEL (Phase 7).
"""

from datetime import datetime, timezone
from sqlalchemy import String, Numeric, Integer, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

VALID_LIFECYCLE_STATES = (
    "NEW",
    "UNDER_REVIEW",
    "CDD_PENDING",
    "ESCALATED",
    "RESOLVED_DISMISSED",
    "RESOLVED_APPROVED"
)


class Case(Base):
    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    primary_tx_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("transactions.tx_id"),
        nullable=False,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="NEW",
        index=True
    )
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="LOW")
    golden_window_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    total_fraud_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.00)
    recoverable_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.00)
    last_disposition_id: Mapped[str] = mapped_column(String(64), nullable=True)
    last_disposition_code: Mapped[str] = mapped_column(String(64), nullable=True)
    last_disposition_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
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
        CheckConstraint(
            f"status IN ('NEW', 'UNDER_REVIEW', 'CDD_PENDING', 'ESCALATED', 'RESOLVED_DISMISSED', 'RESOLVED_APPROVED')",
            name="chk_case_status"
        ),
        Index("idx_cases_status", "status"),
        Index("idx_cases_primary_tx", "primary_tx_id"),
    )

    # Relationships
    primary_transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="cases"
    )
    investigation_reports: Mapped[list["InvestigationReport"]] = relationship(
        "InvestigationReport",
        back_populates="case",
        cascade="all, delete-orphan"
    )
    investigation_runs: Mapped[list["InvestigationRun"]] = relationship(
        "InvestigationRun",
        back_populates="case",
        cascade="all, delete-orphan"
    )
    dispositions: Mapped[list["Disposition"]] = relationship(

        "Disposition",
        back_populates="case"
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        "AuditEvent",
        back_populates="case"
    )
