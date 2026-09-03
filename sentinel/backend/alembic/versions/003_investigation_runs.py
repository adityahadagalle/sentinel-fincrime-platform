"""Investigation Runs Table for Phase 9 Reliability Hardening

Revision ID: 003_investigation_runs
Revises: 002_audit_immutability
Create Date: 2026-09-01 20:00:00.000000

Creates durable PostgreSQL persistence table for investigation run state, stage states,
retry counts, and concurrency management across application process restarts.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '003_investigation_runs'
down_revision: Union[str, None] = '002_audit_immutability'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Dialect-compatible JSON type
JSONType = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        'investigation_runs',
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='RUNNING'),
        sa.Column('current_stage', sa.String(length=32), nullable=False, server_default='NONE'),
        sa.Column('stage_states', JSONType, nullable=False, server_default='{}'),
        sa.Column('summary', JSONType, nullable=False, server_default='{}'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('force_rerun', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('run_id')
    )
    op.create_index('idx_inv_runs_case_id', 'investigation_runs', ['case_id'])
    op.create_index('idx_inv_runs_status', 'investigation_runs', ['status'])
    op.create_index('idx_inv_runs_case_status', 'investigation_runs', ['case_id', 'status'])


def downgrade() -> None:
    op.drop_index('idx_inv_runs_case_status', table_name='investigation_runs')
    op.drop_index('idx_inv_runs_status', table_name='investigation_runs')
    op.drop_index('idx_inv_runs_case_id', table_name='investigation_runs')
    op.drop_table('investigation_runs')
