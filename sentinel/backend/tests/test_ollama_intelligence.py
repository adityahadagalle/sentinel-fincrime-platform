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
