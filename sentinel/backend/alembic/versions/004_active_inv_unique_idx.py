"""Partial Unique Index for Active Investigation Runs

Revision ID: 004_active_inv_unique_idx
Revises: 003_investigation_runs
Create Date: 2026-09-01 20:50:00.000000

Creates a PostgreSQL partial unique index on investigation_runs(case_id) WHERE status = 'RUNNING'.
Provides defense-in-depth against concurrent multi-process duplicate active investigation insertions.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_active_inv_unique_idx'
down_revision: Union[str, None] = '003_investigation_runs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            'uq_idx_inv_runs_case_running',
            'investigation_runs',
            ['case_id'],
            unique=True,
            postgresql_where=sa.text("status = 'RUNNING'")
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index('uq_idx_inv_runs_case_running', table_name='investigation_runs')
