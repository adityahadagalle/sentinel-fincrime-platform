"""
Transaction ORM Model for SENTINEL (Phase 7).
"""

from datetime import datetime, timezone
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Dialect-compatible JSON type
JSONType = JSONB().with_variant(JSON(), "sqlite")


class Transaction(Base):
    __tablename__ = "transactions"

    tx_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sender_account_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("accounts.account_id"),
        nullable=False,
        index=True
    )
    receiver_account_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("accounts.account_id"),
        nullable=False,
        index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    sender_account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[sender_account_id],
        back_populates="sent_transactions"
    )
    receiver_account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[receiver_account_id],
        back_populates="received_transactions"
    )
    cases: Mapped[list["Case"]] = relationship(
        "Case",
        back_populates="primary_transaction"
    )


Index("idx_transactions_sender", Transaction.sender_account_id)
Index("idx_transactions_receiver", Transaction.receiver_account_id)
