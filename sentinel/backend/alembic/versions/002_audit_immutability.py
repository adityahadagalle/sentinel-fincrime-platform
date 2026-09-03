"""Audit Event Immutability Trigger for SENTINEL Phase 7 Step 4

Revision ID: 002_audit_immutability
Revises: 001_initial_schema
Create Date: 2026-09-01 15:00:00.000000

Enforces database-level audit log immutability by creating a PostgreSQL trigger
and PL/pgSQL function that strictly rejects any UPDATE or DELETE operation on
the audit_events table.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_audit_immutability'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CREATE_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION prevent_audit_event_tampering()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Audit log immutability violation: UPDATE operation is forbidden on audit_events (Audit ID: %).', OLD.audit_id
        USING ERRCODE = '55000';
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Audit log immutability violation: DELETE operation is forbidden on audit_events (Audit ID: %).', OLD.audit_id
        USING ERRCODE = '55000';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_TRIGGER = """
CREATE TRIGGER trg_protect_audit_events
BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_event_tampering();
"""

DROP_TRIGGER = """
DROP TRIGGER IF EXISTS trg_protect_audit_events ON audit_events;
"""

DROP_TRIGGER_FUNCTION = """
DROP FUNCTION IF EXISTS prevent_audit_event_tampering();
"""


def upgrade() -> None:
    # Execute trigger function creation and trigger attachment
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(CREATE_TRIGGER_FUNCTION)
        op.execute(CREATE_TRIGGER)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(DROP_TRIGGER)
        op.execute(DROP_TRIGGER_FUNCTION)
