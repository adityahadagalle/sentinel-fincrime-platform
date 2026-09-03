"""
InvestigationReport ORM Model for SENTINEL (Phase 7).
"""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Dialect-compatible JSON type
JSONType = JSONB().with_variant(JSON(), "sqlite")


class InvestigationReport(Base):
    __tablename__ = "investigation_reports"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cases.case_id", ondelete="CASCADE"),
        nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    report_data: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("case_id", "report_type", name="uq_case_report_type"),
    )

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        back_populates="investigation_reports"
    )
