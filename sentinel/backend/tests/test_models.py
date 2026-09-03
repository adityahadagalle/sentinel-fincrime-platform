import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import Numeric, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.models import (
    Base,
    Account,
    Transaction,
    Case,
    InvestigationReport,
    Disposition,
    AuditEvent
)


class TestPhase7ORMModels(unittest.TestCase):

    def test_1_models_import_and_metadata_registered(self):
        """Test 1: All 6 Phase 7 models are registered in Base.metadata.tables."""
        expected_tables = {
            "accounts",
            "transactions",
            "cases",
            "investigation_reports",
            "dispositions",
            "audit_events"
        }
        registered_tables = set(Base.metadata.tables.keys())
        for tbl in expected_tables:
            self.assertIn(tbl, registered_tables)

    def test_2_primary_keys_exist(self):
        """Test 2: Each table defines the required Primary Key."""
        tables = Base.metadata.tables
        self.assertEqual([c.name for c in tables["accounts"].primary_key.columns], ["account_id"])
        self.assertEqual([c.name for c in tables["transactions"].primary_key.columns], ["tx_id"])
        self.assertEqual([c.name for c in tables["cases"].primary_key.columns], ["case_id"])
        self.assertEqual([c.name for c in tables["investigation_reports"].primary_key.columns], ["report_id"])
        self.assertEqual([c.name for c in tables["dispositions"].primary_key.columns], ["disposition_id"])
        self.assertEqual([c.name for c in tables["audit_events"].primary_key.columns], ["audit_id"])

    def test_3_foreign_keys_defined(self):
        """Test 3: Foreign key relationships are accurately defined."""
        tables = Base.metadata.tables

        tx_fks = {fk.column.table.name: fk.parent.name for fk in tables["transactions"].foreign_keys}
        self.assertIn("accounts", tx_fks)

        case_fks = {fk.column.table.name: fk.parent.name for fk in tables["cases"].foreign_keys}
        self.assertEqual(case_fks.get("transactions"), "primary_tx_id")

        report_fks = {fk.column.table.name: fk.parent.name for fk in tables["investigation_reports"].foreign_keys}
        self.assertEqual(report_fks.get("cases"), "case_id")

        disp_fks = {fk.column.table.name: fk.parent.name for fk in tables["dispositions"].foreign_keys}
        self.assertEqual(disp_fks.get("cases"), "case_id")
        self.assertEqual(disp_fks.get("transactions"), "primary_tx_id")

        audit_fks = {fk.column.table.name: fk.parent.name for fk in tables["audit_events"].foreign_keys}
        self.assertEqual(audit_fks.get("cases"), "case_id")
        self.assertEqual(audit_fks.get("transactions"), "primary_tx_id")

    def test_4_monetary_fields_use_numeric(self):
        """Test 4: Monetary fields use NUMERIC type (not Float/Double)."""
        tables = Base.metadata.tables
        self.assertIsInstance(tables["transactions"].c.amount.type, Numeric)
        self.assertIsInstance(tables["cases"].c.total_fraud_amount.type, Numeric)
        self.assertIsInstance(tables["cases"].c.recoverable_amount.type, Numeric)

    def test_5_timestamp_fields_timezone_aware(self):
        """Test 5: Timestamp fields use timezone-aware DateTime."""
        tables = Base.metadata.tables
        self.assertTrue(tables["transactions"].c.timestamp.type.timezone)
        self.assertTrue(tables["cases"].c.created_at.type.timezone)
        self.assertTrue(tables["dispositions"].c.timestamp.type.timezone)
        self.assertTrue(tables["audit_events"].c.timestamp.type.timezone)

    def test_6_jsonb_fields_correctly_typed(self):
        """Test 6: Complex investigation objects use JSON/JSONB fields."""
        tables = Base.metadata.tables
        self.assertTrue(isinstance(tables["transactions"].c.raw_payload.type, (JSONB, JSON)))
        self.assertTrue(isinstance(tables["investigation_reports"].c.report_data.type, (JSONB, JSON)))
        self.assertTrue(isinstance(tables["audit_events"].c.decision_support_summary.type, (JSONB, JSON)))
        self.assertTrue(isinstance(tables["audit_events"].c.traceability_chain.type, (JSONB, JSON)))

    def test_7_case_status_check_constraint_exists(self):
        """Test 7: Case status CheckConstraint is present on cases table."""
        cases_table = Base.metadata.tables["cases"]
        chk_constraints = [c for c in cases_table.constraints if isinstance(c, CheckConstraint)]
        self.assertTrue(any(c.name == "chk_case_status" for c in chk_constraints))

    def test_8_idempotency_and_report_uniqueness_constraints(self):
        """Test 8: Unique constraints exist for idempotency_key and report (case_id, report_type)."""
        tables = Base.metadata.tables

        # Check InvestigationReport unique constraint
        rpt_constraints = [c for c in tables["investigation_reports"].constraints if isinstance(c, UniqueConstraint)]
        self.assertTrue(any(c.name == "uq_case_report_type" for c in rpt_constraints))

        # Check Disposition idempotency_key unique property
        disp_idempotency_col = tables["dispositions"].c.idempotency_key
        self.assertTrue(disp_idempotency_col.unique)

    def test_9_indexes_exist(self):
        """Test 9: Critical query indexes are defined on models."""
        tables = Base.metadata.tables
        case_indexes = {idx.name for idx in tables["cases"].indexes}
        self.assertIn("idx_cases_status", case_indexes)
        self.assertIn("idx_cases_primary_tx", case_indexes)

        tx_indexes = {idx.name for idx in tables["transactions"].indexes}
        self.assertIn("idx_transactions_sender", tx_indexes)
        self.assertIn("idx_transactions_receiver", tx_indexes)

        disp_indexes = {idx.name for idx in tables["dispositions"].indexes}
        self.assertIn("idx_dispositions_case_time", disp_indexes)

        audit_indexes = {idx.name for idx in tables["audit_events"].indexes}
        self.assertIn("idx_audit_events_case_time", audit_indexes)


if __name__ == "__main__":
    unittest.main()
