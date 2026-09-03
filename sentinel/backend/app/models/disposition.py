"""
Disposition ORM Model for SENTINEL (Phase 7).
"""

from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Disposition(Base):
    __tablename__ = "dispositions"

    disposition_id: Mapped[str] = mapped_column(String(64), primary_key=True)
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
    action_code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    analyst_notes: Mapped[str] = mapped_column(Text, nullable=False)
    analyst_id: Mapped[str] = mapped_column(String(64), nullable=False)
    analyst_role: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    previous_case_status: Mapped[str] = mapped_column(String(32), nullable=False)
    new_case_status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_dispositions_case_time", "case_id", timestamp.desc()),
    )

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="dispositions"
    )
    transaction: Mapped["Transaction"] = relationship("Transaction")
