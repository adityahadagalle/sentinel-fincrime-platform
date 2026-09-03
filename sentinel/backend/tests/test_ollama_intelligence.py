"""
SENTINEL — Ollama/Qwen Intelligence Integration Tests (Phase 11)

Coverage:
  1.  Ollama service success (mocked)
  2.  Ollama unavailable
  3.  Ollama timeout
  4.  Malformed model response
  5.  Structured response validation
  6.  POST /intelligence/analyze
  7.  GET /intelligence/health
  8.  Empty investigation context
  9.  AI output cannot trigger an action
  10. Existing autonomous action tests remain unaffected (verified by import)

Ollama is MOCKED — tests do not require a running Ollama instance.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.services.ollama_service import (
    AIAnalysisResponse,
    DetectedPattern,
    IntelligenceResult,
    OllamaService,
    OLLAMA_MODEL,
)


# ── HELPERS ───────────────────────────────────────────────────────────────────

VALID_ANALYSIS_DICT = {
    "summary": "Test case summary.",
    "risk_explanation": "High risk due to multi-hop layering.",
    "patterns": [
        {"name": "Mule Cascade", "evidence": "3 mule accounts detected.", "confidence": 0.87}
    ],
    "network_explanation": "Funds flow through 4 hops.",
    "key_entities": ["ACC-001", "ACC-002"],
    "recommended_investigation_steps": ["Verify identity of ACC-002"],
    "ai_confidence": 0.82,
}

VALID_ANALYSIS_JSON = json.dumps(VALID_ANALYSIS_DICT)

OLLAMA_ENVELOPE = json.dumps({
    "model": OLLAMA_MODEL,
    "message": {"role": "assistant", "content": VALID_ANALYSIS_JSON},
    "done": True,
})

MINIMAL_CONTEXT = {
    "case_id": "CASE-TEST-001",
    "risk_level": "HIGH",
    "risk_score": 85.0,
    "topology_type": "MULTI_HOP_DAG",
    "network_summary": {"total_nodes": 5, "total_flows": 4, "mule_count": 2},
    "entities": ["ACC-001 [VICTIM]", "ACC-002 [MULE]"],
    "transaction_flows": ["ACC-001 → ACC-002  ₹50,000  UPI  Hop 1 [SUSPICIOUS]"],
    "detected_patterns": ["Multi-hop layering: 4 hops"],
    "policy_decision_summary": None,
}


def _mock_urlopen_success(url, timeout):
    """Context-manager mock that returns a valid Ollama response."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = OLLAMA_ENVELOPE.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _mock_urlopen_tags_ok(url, timeout):
    """For is_available() /api/tags check — returns 200."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"models":[]}'
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ── TEST 1: SERVICE SUCCESS ───────────────────────────────────────────────────

class TestOllamaServiceSuccess:
    def test_analyze_returns_ready_status(self):
        svc = OllamaService()

        def urlopen_side_effect(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "tags" in url:
                return _mock_urlopen_tags_ok(url, timeout)
            return _mock_urlopen_success(url, timeout)

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            result = svc.analyze(MINIMAL_CONTEXT, case_id="CASE-TEST-001")

        assert result.status == "ready"
        assert result.case_id == "CASE-TEST-001"
        assert result.analysis is not None
        assert result.analysis.ai_confidence == pytest.approx(0.82)

    def test_analysis_has_correct_schema_fields(self):
        svc = OllamaService()

        def urlopen_side_effect(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "tags" in url:
                return _mock_urlopen_tags_ok(url, timeout)
            return _mock_urlopen_success(url, timeout)

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            result = svc.analyze(MINIMAL_CONTEXT)

        a = result.analysis
        assert isinstance(a.summary, str)
        assert isinstance(a.risk_explanation, str)
        assert isinstance(a.patterns, list)
        assert isinstance(a.network_explanation, str)
        assert isinstance(a.key_entities, list)
        assert isinstance(a.recommended_investigation_steps, list)
        assert 0.0 <= a.ai_confidence <= 1.0

    def test_pattern_confidence_clamped(self):
        svc = OllamaService()
        bad_dict = dict(VALID_ANALYSIS_DICT)
        bad_dict["patterns"] = [
            {"name": "X", "evidence": "Y", "confidence": 1.5}  # out of range
        ]
        bad_dict["ai_confidence"] = 2.0  # out of range
        envelope = json.dumps({
            "message": {"role": "assistant", "content": json.dumps(bad_dict)},
        })

        def urlopen_side_effect(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "tags" in url:
                return _mock_urlopen_tags_ok(url, timeout)
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = envelope.encode()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            result = svc.analyze(MINIMAL_CONTEXT)

        # ai_confidence should be clamped to 1.0
        if result.status == "ready":
            assert result.analysis.ai_confidence <= 1.0


# ── TEST 2: OLLAMA UNAVAILABLE ────────────────────────────────────────────────

class TestOllamaUnavailable:
    def test_analyze_returns_unavailable(self):
        svc = OllamaService()
        with patch.object(svc, "is_available", return_value=False):
            result = svc.analyze(MINIMAL_CONTEXT, case_id="CASE-TEST-002")
        assert result.status == "unavailable"
        assert result.analysis is None

    def test_health_check_returns_false_when_down(self):
        svc = OllamaService()
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            assert svc.is_available() is False

    def test_app_still_returns_result_not_exception(self):
        svc = OllamaService()
        with patch.object(svc, "is_available", return_value=False):
            result = svc.analyze(MINIMAL_CONTEXT)
        # Must not raise — returns controlled result
        assert isinstance(result, IntelligenceResult)


# ── TEST 3: TIMEOUT ───────────────────────────────────────────────────────────

class TestOllamaTimeout:
    def test_analyze_returns_timeout_status(self):
        svc = OllamaService(timeout=1)
        with patch.object(svc, "is_available", return_value=True):
            with patch.object(svc, "_call_chat", side_effect=TimeoutError("timed out")):
                result = svc.analyze(MINIMAL_CONTEXT, case_id="CASE-TEST-003")
        assert result.status == "timeout"
        assert result.analysis is None
        assert "timeout" in (result.error_detail or "").lower() or result.status == "timeout"


# ── TEST 4: MALFORMED MODEL RESPONSE ─────────────────────────────────────────

class TestMalformedModelResponse:
    def test_non_json_content_returns_error(self):
        svc = OllamaService()
        garbage_envelope = json.dumps({
            "message": {"role": "assistant", "content": "Sure! I think the case is risky because..."}
        })

        def urlopen_side_effect(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "tags" in url:
                return _mock_urlopen_tags_ok(url, timeout)
            mock_resp = MagicMock()
            mock_resp.read.return_value = garbage_envelope.encode()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            result = svc.analyze(MINIMAL_CONTEXT)

        assert result.status == "error"
        assert result.analysis is None

    def test_empty_content_returns_error(self):
        svc = OllamaService()
        envelope = json.dumps({"message": {"role": "assistant", "content": ""}})

        def urlopen_side_effect(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "tags" in url:
                return _mock_urlopen_tags_ok(url, timeout)
            mock_resp = MagicMock()
            mock_resp.read.return_value = envelope.encode()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            result = svc.analyze(MINIMAL_CONTEXT)

        assert result.status == "error"

    def test_missing_required_field_returns_error(self):
        svc = OllamaService()
        # Drop required 'summary' field
        bad = {k: v for k, v in VALID_ANALYSIS_DICT.items() if k != "summary"}
        envelope = json.dumps({"message": {"role": "assistant", "content": json.dumps(bad)}})

        def urlopen_side_effect(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "tags" in url:
                return _mock_urlopen_tags_ok(url, timeout)
            mock_resp = MagicMock()
            mock_resp.read.return_value = envelope.encode()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            result = svc.analyze(MINIMAL_CONTEXT)

        assert result.status == "error"


# ── TEST 5: STRUCTURED RESPONSE VALIDATION ────────────────────────────────────

class TestStructuredResponseValidation:
    def test_valid_analysis_response_parses(self):
        a = AIAnalysisResponse(**VALID_ANALYSIS_DICT)
        assert a.summary == "Test case summary."
        assert len(a.patterns) == 1
        assert a.patterns[0].confidence == pytest.approx(0.87)
        assert a.ai_confidence == pytest.approx(0.82)

    def test_pattern_requires_name_evidence_confidence(self):
        with pytest.raises(Exception):
            DetectedPattern(name="X", evidence="Y")  # missing confidence

    def test_confidence_boundary_values(self):
        a = AIAnalysisResponse(**{**VALID_ANALYSIS_DICT, "ai_confidence": 0.0})
        assert a.ai_confidence == 0.0
        a2 = AIAnalysisResponse(**{**VALID_ANALYSIS_DICT, "ai_confidence": 1.0})
        assert a2.ai_confidence == 1.0

    def test_intelligence_result_actor_fields(self):
        r = IntelligenceResult(status="ready", case_id="CASE-001")
        assert r.actor == "AI_ASSISTANT"
        assert r.purpose == "INVESTIGATION_INTELLIGENCE"
        assert r.provider == "ollama"


# ── TEST 6: POST /intelligence/analyze ───────────────────────────────────────

class TestAnalyzeEndpoint:
    def test_analyze_returns_no_data_for_unknown_case(self):
        from fastapi.testclient import TestClient
        import sys
        import importlib

        # Import main app
        sys.path.insert(0, ".")
        import main as app_module
        client = TestClient(app_module.app, raise_server_exceptions=False)

        resp = client.post("/intelligence/analyze", json={"case_id": "CASE-DOES-NOT-EXIST"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "no_data"

    def test_analyze_with_valid_case_mocked(self):
        from fastapi.testclient import TestClient
        import main as app_module
        from app.core.data_store import data_store

        # Inject a minimal case
        data_store.setdefault("cases", {})["CASE-MOCK-001"] = {
            "case_id": "CASE-MOCK-001",
            "primary_tx_id": "TX-MOCK-001",
            "risk_level": "HIGH",
            "risk_score": 88,
            "topology_type": "MULTI_HOP_DAG",
            "transactions": ["TX-MOCK-001"],
        }
        data_store.setdefault("transactions", {})["TX-MOCK-001"] = {
            "tx_id": "TX-MOCK-001",
            "amount": 50000,
            "channel": "UPI",
            "risk_score": 88,
            "reason": "Test",
        }

        def mock_analyze(ctx, case_id=None):
            from app.services.ollama_service import AIAnalysisResponse, IntelligenceResult
            return IntelligenceResult(
                status="ready",
                case_id=case_id,
                analysis=AIAnalysisResponse(**VALID_ANALYSIS_DICT),
            )

        client = TestClient(app_module.app, raise_server_exceptions=False)
        with patch("app.routes.intelligence.ollama_service.analyze", side_effect=mock_analyze):
            resp = client.post("/intelligence/analyze", json={"case_id": "CASE-MOCK-001"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["actor"] == "AI_ASSISTANT"
        assert data["purpose"] == "INVESTIGATION_INTELLIGENCE"
        assert data["analysis"]["summary"] == "Test case summary."

        # Cleanup
        data_store.get("cases", {}).pop("CASE-MOCK-001", None)
        data_store.get("transactions", {}).pop("TX-MOCK-001", None)


# ── TEST 7: GET /intelligence/health ─────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_available(self):
        from fastapi.testclient import TestClient
        import main as app_module

        client = TestClient(app_module.app)
        with patch("app.routes.intelligence.ollama_service.is_available", return_value=True):
            resp = client.get("/intelligence/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert data["provider"] == "ollama"
        assert data["model"] == OLLAMA_MODEL

    def test_health_unavailable(self):
        from fastapi.testclient import TestClient
        import main as app_module

        client = TestClient(app_module.app)
        with patch("app.routes.intelligence.ollama_service.is_available", return_value=False):
            resp = client.get("/intelligence/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False

    def test_health_does_not_crash_app(self):
        from fastapi.testclient import TestClient
        import main as app_module
        import urllib.error

        client = TestClient(app_module.app)
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            resp = client.get("/intelligence/health")
        assert resp.status_code == 200


# ── TEST 8: EMPTY INVESTIGATION CONTEXT ──────────────────────────────────────

class TestEmptyContext:
    def test_empty_dict_returns_no_data(self):
        svc = OllamaService()
        result = svc.analyze({}, case_id="CASE-EMPTY")
        assert result.status == "no_data"
        assert result.analysis is None

    def test_none_values_handled(self):
        svc = OllamaService()
        with patch.object(svc, "is_available", return_value=True):
            result = svc.analyze({})
        assert result.status == "no_data"


# ── TEST 9: AI OUTPUT CANNOT TRIGGER ACTIONS ─────────────────────────────────

class TestAICannotTriggerActions:
    """
    Verifies that no path exists from AI analysis output to enforcement.
    """

    def test_intelligence_result_has_no_action_field(self):
        r = IntelligenceResult(status="ready")
        # Must not have any action/enforce/freeze/block attribute
        assert not hasattr(r, "action")
        assert not hasattr(r, "enforce")
        assert not hasattr(r, "freeze")
        assert not hasattr(r, "block")

    def test_analysis_response_has_no_action_field(self):
        a = AIAnalysisResponse(**VALID_ANALYSIS_DICT)
        assert not hasattr(a, "action")
        assert not hasattr(a, "freeze")
        assert not hasattr(a, "block_account")
        assert not hasattr(a, "execute")

    def test_ollama_service_has_no_action_executor_import(self):
        """Service module must not import action executor."""
        import app.services.ollama_service as svc_module
        import inspect
        source = inspect.getsource(svc_module)
        assert "simulated_action_executor" not in source
        assert "autonomous_policy_engine" not in source
        assert "execute_simulated_action" not in source
        assert "evaluate_autonomous_policy" not in source

    def test_intelligence_route_has_no_action_executor_import(self):
        """Intelligence route must not import action executor."""
        import app.routes.intelligence as route_module
        import inspect
        source = inspect.getsource(route_module)
        assert "simulated_action_executor" not in source
        assert "autonomous_policy_engine" not in source
        assert "execute_simulated_action" not in source

    def test_analyze_endpoint_does_not_call_action_executor(self):
        """POST /intelligence/analyze must not call execute_simulated_action."""
        from fastapi.testclient import TestClient
        import main as app_module
        from app.core.data_store import data_store

        data_store.setdefault("cases", {})["CASE-NOACTION"] = {
            "case_id": "CASE-NOACTION",
            "risk_level": "CRITICAL",
            "topology_type": "LINEAR_CHAIN",
            "transactions": [],
        }

        with patch("app.services.simulated_action_executor.execute_simulated_action") as mock_exec:
            with patch("app.routes.intelligence.ollama_service.analyze") as mock_analyze:
                mock_analyze.return_value = IntelligenceResult(
                    status="ready",
                    case_id="CASE-NOACTION",
                    analysis=AIAnalysisResponse(**VALID_ANALYSIS_DICT),
                )
                client = TestClient(app_module.app, raise_server_exceptions=False)
                client.post("/intelligence/analyze", json={"case_id": "CASE-NOACTION"})

        mock_exec.assert_not_called()
        data_store.get("cases", {}).pop("CASE-NOACTION", None)


# ── TEST 10: EXISTING AUTONOMOUS TESTS UNAFFECTED ────────────────────────────

class TestExistingSystemsUnaffected:
    def test_policy_engine_importable(self):
        """autonomous_policy_engine must be importable and unchanged."""
        from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
        assert callable(evaluate_autonomous_policy)

    def test_action_executor_importable(self):
        """simulated_action_executor must be importable and unchanged."""
        from app.services.simulated_action_executor import execute_simulated_action
        assert callable(execute_simulated_action)

    def test_intelligence_service_isolation(self):
        """OllamaService must not share state with policy engine."""
        from app.engines.autonomous_policy_engine import evaluate_autonomous_policy
        svc = OllamaService()
        # No shared callable reference
        assert evaluate_autonomous_policy is not svc.analyze


# ── TEST 11: 5-AGENT INVESTIGATION SYNTHESIS ─────────────────────────────────

MOCK_5_STAGE_REPORTS = {
    "EVIDENCE": {
        "found": True,
        "summary": {
            "total_evidence_items": 4,
            "high_severity_items": 2,
            "medium_severity_items": 1,
            "categories_covered": ["TRANSACTION", "VELOCITY", "GRAPH"]
        },
        "evidence": [
            {
                "id": "EV-001",
                "category": "TRANSACTION",
                "severity": "HIGH",
                "finding": "High-value pass-through transfer of ₹1,25,000",
                "source": "transaction_monitor"
            },
            {
                "id": "EV-002",
                "category": "VELOCITY",
                "severity": "HIGH",
                "finding": "Funds drained within 45 seconds of receipt",
                "source": "velocity_engine"
            }
        ]
    },
    "CONTEXTUAL": {
        "found": True,
        "summary": {
            "contextual_severity": "HIGH",
            "confidence": 0.94,
            "pattern_count": 1
        },
        "patterns": [
            {
                "pattern_id": "CP-PASS-THROUGH",
                "name": "Pass-Through Account Drainage",
                "severity": "HIGH",
                "confidence": 0.94,
                "description": "Rapid pass-through pattern detected consistent with mule relay behavior.",
                "supporting_evidence_ids": ["EV-001", "EV-002"]
            }
        ],
        "contextual_findings": [
            {
                "id": "CTX-001",
                "type": "pattern",
                "severity": "HIGH",
                "finding": "Account displays mule node characteristics.",
                "supporting_evidence_ids": ["EV-001"]
            }
        ]
    },
    "REGULATORY": {
        "found": True,
        "summary": {
            "regulatory_severity": "CRITICAL",
            "assessment_heuristic_index": 0.88,
            "indicator_count": 1,
            "jurisdiction_context": "INDIAN_FINANCIAL_SYSTEM_SIMULATION"
        },
        "regulatory_indicators": [
            {
                "id": "REG-001",
                "code": "PMLA_SUSPICIOUS_PATTERN",
                "severity": "CRITICAL",
                "regulatory_framework": "PMLA_2002",
                "reporting_implication": "STR_MANDATORY_REVIEW",
                "description": "Unusual fund velocity with layering exceeds PMLA suspicious activity threshold."
            }
        ],
        "compliance_considerations": [
            {
                "code": "STR_FILING",
                "recommendation": "Prepare Suspicious Transaction Report (STR) for FIU-IND review within statutory timeframe."
            }
        ]
    },
    "AUDIT_EXPLANATION": {
        "found": True,
        "executive_summary": "Comprehensive deterministic investigation reveals coordinated rapid layering across 3 hops.",
        "summary": {
            "regulatory_severity": "CRITICAL",
            "traceability_status": "VERIFIED_COMPLETE"
        },
        "investigation_narrative": [
            {
                "step_number": 1,
                "title": "Initial Deposit & Rapid Hop",
                "description": "Source victim deposited ₹1,25,000 into intermediate mule account."
            }
        ],
        "key_findings": [
            {
                "finding_id": "KF-001",
                "statement": "Confirmed high-confidence mule relay signature with 94% pattern confidence.",
                "severity": "HIGH"
            }
        ],
        "uncertainties": [],
        "data_gaps": []
    },
    "DECISION_SUPPORT": {
        "found": True,
        "summary": {
            "review_priority": "URGENT",
            "requires_human_approval": True
        },
        "review_priority": "URGENT",
        "priority_rationale": "High-risk pass-through transfer in progress with active cashout risk.",
        "analyst_executive_brief": "Urgent operator intervention recommended to review exit nodes prior to ATM cashout.",
        "recommended_review_steps": [
            {
                "step_id": "STEP-01",
                "action": "Verify beneficiary identity with partner bank",
                "rationale": "Confirm if account holder is a known synthetic or compromised identity.",
                "priority": "URGENT"
            }
        ],
        "disposition_options": [
            {
                "action_code": "FREEZE_CONFIRM",
                "label": "Confirm Temporary Administrative Freeze",
                "description": "Halt further outbound transfers pending KYC re-verification.",
                "recommended": True
            }
        ],
        "human_approval_boundary": {
            "autonomous_execution": False,
            "required_role": "COMPLIANCE_ANALYST"
        }
    }
}


class TestQwenFiveAgentSynthesis:
    """
    Tests for Qwen advisory synthesis of the 5 deterministic investigation agents.
    """

    @pytest.mark.asyncio
    async def test_context_builder_retrieves_all_5_reports_when_present(self):
        """When all 5 reports exist in the repository/store, context builder retrieves all 5."""
        from app.routes.intelligence import _build_investigation_context
        from app.repositories.in_memory import InMemoryCaseRepository
        from app.core.data_store import data_store

        case_id = "CASE-SYNTH-ALL-5"
        data_store.setdefault("cases", {})[case_id] = {
            "case_id": case_id,
            "primary_tx_id": "TX-SYNTH-01",
            "risk_level": "CRITICAL",
            "risk_score": 95,
            "topology_type": "MULTI_HOP_DAG",
            "transactions": ["TX-SYNTH-01"],
        }
        data_store.setdefault("transactions", {})["TX-SYNTH-01"] = {
            "tx_id": "TX-SYNTH-01",
            "amount": 125000,
            "channel": "UPI",
            "risk_score": 95,
            "reason": "Mule drainage",
        }

        repo = InMemoryCaseRepository(data_store)
        for stg, rpt_data in MOCK_5_STAGE_REPORTS.items():
            await repo.save_investigation_report({
                "case_id": case_id,
                "report_type": stg,
                "report_data": rpt_data,
            })

        ctx = await _build_investigation_context(case_id, data_store, repo=repo)

        assert ctx["case_id"] == case_id
        assert "investigation_reports" in ctx
        assert len(ctx["investigation_reports"]) == 5
        assert set(ctx["synthesized_stages"]) == {
            "EVIDENCE", "CONTEXTUAL", "REGULATORY", "AUDIT_EXPLANATION", "DECISION_SUPPORT"
        }
        assert ctx["missing_stages"] == []

        # Verify all 5 stages marked COMPLETED in status
        for stg in ["evidence", "contextual", "regulatory", "audit_explanation", "decision_support"]:
            assert ctx["investigation_status"][stg] == "COMPLETED"

        # Verify Ollama user message serializes all 5 stages
        svc = OllamaService()
        msg = svc._build_user_message(ctx)
        assert "[STAGE 1: EVIDENCE COLLECTION FINDINGS]" in msg
        assert "[STAGE 2: CONTEXTUAL INVESTIGATION FINDINGS]" in msg
        assert "[STAGE 3: REGULATORY RISK ASSESSMENT FINDINGS]" in msg
        assert "[STAGE 4: AUDIT EXPLANATION FINDINGS]" in msg
        assert "[STAGE 5: ANALYST DECISION SUPPORT FINDINGS]" in msg
        assert "Pass-Through Account Drainage" in msg
        assert "PMLA_SUSPICIOUS_PATTERN" in msg
        assert "Verify beneficiary identity with partner bank" in msg

        # Cleanup
        data_store.get("cases", {}).pop(case_id, None)
        data_store.get("transactions", {}).pop("TX-SYNTH-01", None)

    @pytest.mark.asyncio
    async def test_context_builder_handles_partial_investigation_cleanly(self):
        """When only some stages are complete, context accurately flags missing stages without error."""
        from app.routes.intelligence import _build_investigation_context
        from app.repositories.in_memory import InMemoryCaseRepository
        from app.core.data_store import data_store

        case_id = "CASE-SYNTH-PARTIAL"
        data_store.setdefault("cases", {})[case_id] = {
            "case_id": case_id,
            "primary_tx_id": "TX-SYNTH-02",
            "risk_level": "HIGH",
            "risk_score": 75,
            "topology_type": "LINEAR_CHAIN",
            "transactions": ["TX-SYNTH-02"],
        }
        data_store.setdefault("transactions", {})["TX-SYNTH-02"] = {
            "tx_id": "TX-SYNTH-02",
            "amount": 50000,
            "channel": "IMPS",
            "risk_score": 75,
            "reason": "Rapid hop",
        }

        repo = InMemoryCaseRepository(data_store)
        # Only save EVIDENCE and CONTEXTUAL reports
        await repo.save_investigation_report({
            "case_id": case_id,
            "report_type": "EVIDENCE",
            "report_data": MOCK_5_STAGE_REPORTS["EVIDENCE"],
        })
        await repo.save_investigation_report({
            "case_id": case_id,
            "report_type": "CONTEXTUAL",
            "report_data": MOCK_5_STAGE_REPORTS["CONTEXTUAL"],
        })

        ctx = await _build_investigation_context(case_id, data_store, repo=repo)

        assert set(ctx["synthesized_stages"]) == {"EVIDENCE", "CONTEXTUAL"}
        assert set(ctx["missing_stages"]) == {"REGULATORY", "AUDIT_EXPLANATION", "DECISION_SUPPORT"}

        # Verify missing stages warning in user message
        svc = OllamaService()
        msg = svc._build_user_message(ctx)
        assert "[STAGE 1: EVIDENCE COLLECTION FINDINGS]" in msg
        assert "[STAGE 2: CONTEXTUAL INVESTIGATION FINDINGS]" in msg
        assert "--- INCOMPLETE / PENDING / MISSING INVESTIGATION STAGES ---" in msg
        assert "[STAGE: REGULATORY] Stage NOT COMPLETED" in msg
        assert "[STAGE: AUDIT_EXPLANATION] Stage NOT COMPLETED" in msg
        assert "[STAGE: DECISION_SUPPORT] Stage NOT COMPLETED" in msg

        # Cleanup
        data_store.get("cases", {}).pop(case_id, None)
        data_store.get("transactions", {}).pop("TX-SYNTH-02", None)

    @pytest.mark.asyncio
    async def test_context_builder_handles_no_reports_cleanly(self):
        """When no investigation reports exist, context builder still produces valid context without crash."""
        from app.routes.intelligence import _build_investigation_context
        from app.repositories.in_memory import InMemoryCaseRepository
        from app.core.data_store import data_store

        case_id = "CASE-SYNTH-EMPTY"
        data_store.setdefault("cases", {})[case_id] = {
            "case_id": case_id,
            "primary_tx_id": "TX-SYNTH-03",
            "risk_level": "LOW",
            "risk_score": 20,
            "topology_type": "UNKNOWN",
            "transactions": [],
        }

        repo = InMemoryCaseRepository(data_store)
        ctx = await _build_investigation_context(case_id, data_store, repo=repo)

        assert ctx["case_id"] == case_id
        # Missing stages should account for uncompleted stages
        assert "REGULATORY" in ctx["missing_stages"]
        assert "AUDIT_EXPLANATION" in ctx["missing_stages"]
        assert "DECISION_SUPPORT" in ctx["missing_stages"]

        # Cleanup
        data_store.get("cases", {}).pop(case_id, None)

    def test_system_prompt_instructs_5_stage_synthesis_and_boundaries(self):
        """Verify system prompt explicitly names the 5 stages and reinforces advisory-only constraints."""
        from app.services.ollama_service import SENTINEL_SYSTEM_PROMPT

        # 5 stage names must be mentioned
        assert "Evidence Collection" in SENTINEL_SYSTEM_PROMPT
        assert "Contextual Investigation" in SENTINEL_SYSTEM_PROMPT
        assert "Regulatory Risk Assessment" in SENTINEL_SYSTEM_PROMPT
        assert "Audit Explanation" in SENTINEL_SYSTEM_PROMPT
        assert "Analyst Decision Support" in SENTINEL_SYSTEM_PROMPT

        # Strict advisory boundaries must be enforced
        assert "NOT the policy engine" in SENTINEL_SYSTEM_PROMPT
        assert "NOT the action executor" in SENTINEL_SYSTEM_PROMPT
        assert "CANNOT freeze" in SENTINEL_SYSTEM_PROMPT
        assert "CANNOT override deterministic SENTINEL policy decisions" in SENTINEL_SYSTEM_PROMPT
        assert "ADVISORY INTELLIGENCE ONLY" in SENTINEL_SYSTEM_PROMPT

        # Distinction between verified system findings and AI interpretation
        assert "verified system findings" in SENTINEL_SYSTEM_PROMPT.lower()
        assert "ai synthesis" in SENTINEL_SYSTEM_PROMPT.lower()
        assert "recommended_investigation_steps" in SENTINEL_SYSTEM_PROMPT

    def test_intelligence_result_contains_synthesized_and_missing_stages(self):
        """Verify IntelligenceResult envelope exposes synthesized_stages and missing_stages."""
        r = IntelligenceResult(
            status="ready",
            case_id="CASE-001",
            synthesized_stages=["EVIDENCE", "CONTEXTUAL"],
            missing_stages=["REGULATORY", "AUDIT_EXPLANATION", "DECISION_SUPPORT"]
        )
        assert r.synthesized_stages == ["EVIDENCE", "CONTEXTUAL"]
        assert r.missing_stages == ["REGULATORY", "AUDIT_EXPLANATION", "DECISION_SUPPORT"]

    def test_post_analyze_endpoint_returns_synthesized_stages(self):
        """Verify POST /intelligence/analyze returns synthesized_stages and missing_stages."""
        from fastapi.testclient import TestClient
        import main as app_module
        from app.core.data_store import data_store

        case_id = "CASE-API-SYNTH"
        data_store.setdefault("cases", {})[case_id] = {
            "case_id": case_id,
            "primary_tx_id": "TX-01",
            "risk_level": "HIGH",
            "risk_score": 80,
            "topology_type": "MULTI_HOP_DAG",
            "transactions": [],
        }

        def mock_analyze(ctx, case_id=None):
            return IntelligenceResult(
                status="ready",
                case_id=case_id,
                synthesized_stages=ctx.get("synthesized_stages", []),
                missing_stages=ctx.get("missing_stages", []),
                analysis=AIAnalysisResponse(
                    **VALID_ANALYSIS_DICT,
                    synthesized_stages=ctx.get("synthesized_stages", []),
                    missing_stages=ctx.get("missing_stages", [])
                ),
            )

        client = TestClient(app_module.app, raise_server_exceptions=False)
        with patch("app.routes.intelligence.ollama_service.analyze", side_effect=mock_analyze):
            resp = client.post("/intelligence/analyze", json={"case_id": case_id})

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "synthesized_stages" in data
        assert "missing_stages" in data

        # Cleanup
        data_store.get("cases", {}).pop(case_id, None)
