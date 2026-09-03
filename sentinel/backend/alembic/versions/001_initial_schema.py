"""Initial Schema for SENTINEL Phase 7

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Accounts
    op.create_table(
        'accounts',
        sa.Column('account_id', sa.String(length=64), nullable=False),
        sa.Column('kyc_status', sa.String(length=32), nullable=False, server_default='PENDING'),
        sa.Column('risk_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('account_id')
    )

    # 2. Transactions
    op.create_table(
        'transactions',
        sa.Column('tx_id', sa.String(length=64), nullable=False),
        sa.Column('sender_account_id', sa.String(length=64), nullable=False),
        sa.Column('receiver_account_id', sa.String(length=64), nullable=False),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False, server_default='INR'),
        sa.Column('channel', sa.String(length=32), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['sender_account_id'], ['accounts.account_id'], ),
        sa.ForeignKeyConstraint(['receiver_account_id'], ['accounts.account_id'], ),
        sa.PrimaryKeyConstraint('tx_id')
    )
    op.create_index('idx_transactions_sender', 'transactions', ['sender_account_id'], unique=False)
    op.create_index('idx_transactions_receiver', 'transactions', ['receiver_account_id'], unique=False)

    # 3. Cases
    op.create_table(
        'cases',
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('primary_tx_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='NEW'),
        sa.Column('risk_level', sa.String(length=16), nullable=False, server_default='LOW'),
        sa.Column('golden_window_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('total_fraud_amount', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0.00'),
        sa.Column('recoverable_amount', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0.00'),
        sa.Column('last_disposition_id', sa.String(length=64), nullable=True),
        sa.Column('last_disposition_code', sa.String(length=64), nullable=True),
        sa.Column('last_disposition_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('NEW', 'UNDER_REVIEW', 'CDD_PENDING', 'ESCALATED', 'RESOLVED_DISMISSED', 'RESOLVED_APPROVED')", name='chk_case_status'),
        sa.ForeignKeyConstraint(['primary_tx_id'], ['transactions.tx_id'], ),
        sa.PrimaryKeyConstraint('case_id')
    )
    op.create_index('idx_cases_status', 'cases', ['status'], unique=False)
    op.create_index('idx_cases_primary_tx', 'cases', ['primary_tx_id'], unique=False)

    # 4. Investigation Reports
    op.create_table(
        'investigation_reports',
        sa.Column('report_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('report_type', sa.String(length=32), nullable=False),
        sa.Column('report_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('report_id'),
        sa.UniqueConstraint('case_id', 'report_type', name='uq_case_report_type')
    )

    # 5. Dispositions
    op.create_table(
        'dispositions',
        sa.Column('disposition_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('primary_tx_id', sa.String(length=64), nullable=False),
        sa.Column('action_code', sa.String(length=64), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('analyst_notes', sa.Text(), nullable=False),
        sa.Column('analyst_id', sa.String(length=64), nullable=False),
        sa.Column('analyst_role', sa.String(length=64), nullable=False),
        sa.Column('risk_acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('previous_case_status', sa.String(length=32), nullable=False),
        sa.Column('new_case_status', sa.String(length=32), nullable=False),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ),
        sa.ForeignKeyConstraint(['primary_tx_id'], ['transactions.tx_id'], ),
        sa.PrimaryKeyConstraint('disposition_id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('idx_dispositions_case_time', 'dispositions', ['case_id', sa.text('timestamp DESC')], unique=False)

    # 6. Audit Events
    op.create_table(
        'audit_events',
        sa.Column('audit_id', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False, server_default='CASE_DISPOSITION_MUTATION'),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('primary_tx_id', sa.String(length=64), nullable=False),
        sa.Column('analyst_id', sa.String(length=64), nullable=False),
        sa.Column('analyst_role', sa.String(length=64), nullable=False),
        sa.Column('action_code', sa.String(length=64), nullable=False),
        sa.Column('previous_case_status', sa.String(length=32), nullable=False),
        sa.Column('new_case_status', sa.String(length=32), nullable=False),
        sa.Column('analyst_notes', sa.Text(), nullable=False),
        sa.Column('risk_acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('decision_support_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('traceability_chain', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ),
        sa.ForeignKeyConstraint(['primary_tx_id'], ['transactions.tx_id'], ),
        sa.PrimaryKeyConstraint('audit_id')
    )
    op.create_index('idx_audit_events_case_time', 'audit_events', ['case_id', sa.text('timestamp DESC')], unique=False)


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('dispositions')
    op.drop_table('investigation_reports')
    op.drop_table('cases')
    op.drop_table('transactions')
    op.drop_table('accounts')
