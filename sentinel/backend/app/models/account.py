"""
Account ORM Model for SENTINEL (Phase 7).
"""

from datetime import datetime, timezone
from sqlalchemy import String, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kyc_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    risk_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.0)
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

    # Relationships
    sent_transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="Transaction.sender_account_id",
        back_populates="sender_account"
    )
    received_transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="Transaction.receiver_account_id",
        back_populates="receiver_account"
    )
