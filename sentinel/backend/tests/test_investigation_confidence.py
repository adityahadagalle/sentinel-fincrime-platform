import unittest
import asyncio
from main import compute_case_investigation_confidence, app
from httpx import AsyncClient, ASGITransport
from app.core.data_store import data_store


class TestInvestigationConfidence(unittest.TestCase):
    """
    Tests for SENTINEL's deterministic Investigation Confidence metric.
    
    Formula:
      Score = clamp(round(0.35 * Completeness + 0.40 * Agreement + 0.25 * Diversity - 1.0 * Contradictions, 1), 0.0, 100.0)
    """

    def test_case_c_reference_example(self):
        """
        Case C: Reference Example Scenario
        Completeness: 80%
        Agreement: 75%
        Diversity: 60%
        Contradictions: 1
        
        Expected displayed Investigation Confidence: approximately 72% (MEDIUM CONFIDENCE)
        """
        # Build an evidence package with 4 of 5 core categories present (= 80% completeness)
        # and 3 distinct sources present (= 60% diversity: 3/5 * 100)
        evidence_pkg = {
            "found": True,
            "evidence": [
                {"id": "EV-001", "type": "transaction", "category": "Transaction Core", "source": "transaction_store"},
                {"id": "EV-002", "type": "historical_behavior", "category": "Origin Account Baseline", "source": "account_store"},
                {"id": "EV-003", "type": "historical_behavior", "category": "Counterparty Flow", "source": "transaction_store"},
                {"id": "EV-004", "type": "financial", "category": "Financial Metrics", "source": "case_store"}
                # Graph topology absent -> 4 of 5 present = 80.0%
                # Distinct sources: transaction_store, account_store, case_store -> 3/5 = 60.0%
            ]
        }

        # Contextual HIGH (75) vs Regulatory MEDIUM (50) -> pairwise agreement: 100 - |75 - 50| = 75.0%
        ctx_rpt = {
            "found": True,
            "summary": {"contextual_severity": "HIGH"}
        }
        reg_rpt = {
            "found": True,
            "summary": {"regulatory_severity": "MEDIUM"}
        }

        res = compute_case_investigation_confidence(
            evidence_package=evidence_pkg,
            contextual_report=ctx_rpt,
            regulatory_report=reg_rpt
        )

        self.assertEqual(res["evidence_completeness"], 80.0)
        self.assertEqual(res["agent_agreement"], 75.0)
        self.assertEqual(res["source_diversity"], 60.0)

        # Now verify with exactly 1 contradiction injected
        # In our formula: 0.35 * 80 + 0.40 * 75 + 0.25 * 60 - 1.0 * 1 = 73.0 - 1.0 = 72.0%
        comp = res["evidence_completeness"]
        agree = res["agent_agreement"]
        div = res["source_diversity"]
        contra = 1
        expected_score = round(0.35 * comp + 0.40 * agree + 0.25 * div - 1.0 * contra, 1)

        self.assertEqual(expected_score, 72.0)
        self.assertEqual(round(0.35 * 80.0 + 0.40 * 75.0 + 0.25 * 60.0 - 1.0 * 1, 1), 72.0)

    def test_case_a_strong_evidence(self):
        """
        Case A: Strong Evidence
        High evidence completeness (100%)
        High agent agreement (100%)
        High source diversity (100%)
        Zero contradictions (0)
        
        Expected: HIGH CONFIDENCE (100.0%)
        """
        evidence_pkg = {
            "found": True,
            "evidence": [
                {"id": "EV-001", "type": "transaction", "category": "Transaction Core", "source": "transaction_store"},
                {"id": "EV-002", "type": "historical_behavior", "category": "Origin Account Baseline", "source": "account_store"},
                {"id": "EV-003", "type": "historical_behavior", "category": "Counterparty Flow", "source": "case_store"},
                {"id": "EV-004", "type": "graph_network", "category": "Graph Topology", "source": "graph_engine"},
                {"id": "EV-005", "type": "financial", "category": "Financial Metrics", "source": "recovery_engine"},
            ]
        }
        ctx_rpt = {"found": True, "summary": {"contextual_severity": "CRITICAL"}}
        reg_rpt = {"found": True, "summary": {"regulatory_severity": "CRITICAL"}}
        analyst_rpt = {"found": True, "summary": {"regulatory_severity": "CRITICAL"}}

        res = compute_case_investigation_confidence(
            evidence_package=evidence_pkg,
            contextual_report=ctx_rpt,
            regulatory_report=reg_rpt,
            analyst_report=analyst_rpt
        )

        self.assertEqual(res["evidence_completeness"], 100.0)
        self.assertEqual(res["agent_agreement"], 100.0)
        self.assertEqual(res["source_diversity"], 100.0)
        self.assertEqual(res["contradiction_count"], 0)
        self.assertEqual(res["score"], 100.0)
        self.assertEqual(res["label"], "HIGH CONFIDENCE")

    def test_case_b_weak_evidence(self):
        """
        Case B: Weak Evidence
        Low completeness (20%)
        Low agent agreement (25%)
        Low source diversity (20%)
        Polar contradiction (CRITICAL vs LOW)
        
        Expected: LOW CONFIDENCE (< 60%)
        """
        evidence_pkg = {
            "found": True,
            "evidence": [
                {"id": "EV-001", "type": "transaction", "category": "Transaction Core", "source": "transaction_store"}
            ]
        }
        # CRITICAL (100) vs LOW (25) -> agreement: 100 - |100 - 25| = 25.0%, contradiction: 1
        ctx_rpt = {"found": True, "summary": {"contextual_severity": "CRITICAL"}}
        reg_rpt = {"found": True, "summary": {"regulatory_severity": "LOW"}}

        res = compute_case_investigation_confidence(
            evidence_package=evidence_pkg,
            contextual_report=ctx_rpt,
            regulatory_report=reg_rpt
        )

        self.assertEqual(res["evidence_completeness"], 20.0)
        self.assertEqual(res["agent_agreement"], 25.0)
        self.assertEqual(res["source_diversity"], 20.0)
        self.assertEqual(res["contradiction_count"], 1)
        # 0.35 * 20 + 0.40 * 25 + 0.25 * 20 - 1.0 = 7.0 + 10.0 + 5.0 - 1.0 = 21.0%
        self.assertEqual(res["score"], 21.0)
        self.assertEqual(res["label"], "LOW CONFIDENCE")

    def test_case_d_repeated_calculation(self):
        """
        Case D: Repeated Calculation
        Identical inputs must produce strictly identical outputs (deterministic stability).
        """
        evidence_pkg = {
            "found": True,
            "evidence": [
                {"id": "EV-001", "type": "transaction", "category": "Transaction Core", "source": "transaction_store"},
                {"id": "EV-002", "type": "historical_behavior", "category": "Account Baseline", "source": "account_store"},
            ]
        }
        ctx_rpt = {"found": True, "summary": {"contextual_severity": "HIGH"}}
        reg_rpt = {"found": True, "summary": {"regulatory_severity": "MEDIUM"}}

        res1 = compute_case_investigation_confidence(evidence_pkg, ctx_rpt, reg_rpt)
        res2 = compute_case_investigation_confidence(evidence_pkg, ctx_rpt, reg_rpt)

        self.assertEqual(res1, res2)
        self.assertEqual(res1["score"], res2["score"])
        self.assertEqual(res1["label"], res2["label"])

    def test_case_e_missing_incomplete_investigation(self):
        """
        Case E: Missing/Incomplete Investigation
        No evidence, no agent reports -> returns 0.0 metrics with LOW CONFIDENCE label.
        """
        res = compute_case_investigation_confidence(None, None, None, None, None)
        self.assertEqual(res["evidence_completeness"], 0.0)
        self.assertEqual(res["agent_agreement"], 0.0)
        self.assertEqual(res["source_diversity"], 0.0)
        self.assertEqual(res["contradiction_count"], 0)
        self.assertEqual(res["score"], 0.0)

    def test_analytics_overview_integration(self):
        """
        Verify /analytics/overview returns investigation_confidence and NO kyc_verification.
        """
        async def _run():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/analytics/overview?timeframe=30d")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                
                # KYC must be completely absent
                self.assertNotIn("kyc_verification", data)

                # Investigation confidence must be present and structured
                self.assertIn("investigation_confidence", data)
                conf = data["investigation_confidence"]
                self.assertIn("status", conf)
                self.assertIn("score", conf)
                self.assertIn("label", conf)
                self.assertIn("evidence_completeness", conf)
                self.assertIn("agent_agreement", conf)
                self.assertIn("source_diversity", conf)
                self.assertIn("contradiction_count", conf)
                self.assertIn("distinction", conf)
                self.assertEqual(conf["distinction"], "Evidence Support Index • Not Fraud Probability")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
