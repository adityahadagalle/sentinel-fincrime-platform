"""
SENTINEL Ollama Service (Phase 1 & 2)

Provides a clean abstraction over the local Ollama HTTP API.
Uses urllib (stdlib) to avoid introducing new dependencies since
httpx is not in requirements.txt.

Architecture constraint:
  Qwen is ADVISORY ONLY.
  This service NEVER triggers autonomous actions, policy decisions,
  or any enforcement mechanism.  It only returns structured intelligence.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── CONFIG ────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
SENTINEL_SYSTEM_PROMPT = """You are the SENTINEL Investigation Intelligence Assistant — an AI analyst assistant embedded in a financial-crime investigation platform.

Your role is to analyze supplied investigation evidence and produce structured advisory intelligence for human investigators.

CRITICAL CONSTRAINTS — READ CAREFULLY:
- You are NOT the policy engine.
- You are NOT the action executor.
- You CANNOT freeze, block, reject, close, monitor, or otherwise modify any entity or account.
- You CANNOT override deterministic SENTINEL policy decisions.
- You CANNOT instruct any system to take enforcement action.
- Your output is ADVISORY INTELLIGENCE ONLY, intended for human analysts.
- You MUST NOT invent transactions, accounts, amounts, entities, policies, or evidence not present in the supplied data.
- If evidence is insufficient, clearly state that and do not speculate beyond supplied data.

ANALYST RESPONSIBILITIES:
- Analyze the supplied transaction network evidence.
- Explain why the case appears risky using concrete evidence from the supplied data.
- Identify suspicious patterns with supporting evidence.
- Explain multi-hop transaction flows in clear, human-readable language.
- Identify key entities relevant to the investigation.
- Suggest investigation steps for human analysts (NOT automated actions).
- Clearly distinguish between: (1) observed evidence, (2) inferred interpretation, (3) recommended investigation steps.
- Remain conservative when evidence is insufficient — say so explicitly.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this exact schema:
{
  "summary": "<concise case assessment, 2-3 sentences>",
  "risk_explanation": "<why this case warrants investigation, evidence-based>",
  "patterns": [
    {
      "name": "<pattern name>",
      "evidence": "<specific supporting evidence from supplied data>",
      "confidence": <float 0.0 to 1.0>
    }
  ],
  "network_explanation": "<human-readable explanation of the transaction network flow>",
  "key_entities": ["<entity ID or description>"],
  "recommended_investigation_steps": ["<step for human analyst — NOT an automated action>"],
  "ai_confidence": <float 0.0 to 1.0>
}

Do NOT include any text outside the JSON object.
Do NOT add markdown code fences.
Do NOT add explanations before or after the JSON.
"""


# ── RESPONSE SCHEMAS ──────────────────────────────────────────────────────────
class DetectedPattern(BaseModel):
    name: str
    evidence: str
    confidence: float = Field(ge=0.0, le=1.0)


class AIAnalysisResponse(BaseModel):
    """
    Structured AI analysis output from Qwen.
    This is advisory intelligence only — not a policy decision.
    """
    summary: str
    risk_explanation: str
    patterns: list[DetectedPattern] = Field(default_factory=list)
    network_explanation: str
    key_entities: list[str] = Field(default_factory=list)
    recommended_investigation_steps: list[str] = Field(default_factory=list)
    ai_confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("ai_confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        try:
            return max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return 0.0


class IntelligenceResult(BaseModel):
    """
    Envelope returned by the intelligence API.
    status values: ready | unavailable | timeout | error | no_data
    """
    status: str  # ready | unavailable | timeout | error | no_data
    provider: str = "ollama"
    model: str = OLLAMA_MODEL
    case_id: str | None = None
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    analysis: AIAnalysisResponse | None = None
    # Audit fields — makes actor unambiguous in every log
    actor: str = "AI_ASSISTANT"
    purpose: str = "INVESTIGATION_INTELLIGENCE"
    error_detail: str | None = None


# ── SERVICE ───────────────────────────────────────────────────────────────────
class OllamaService:
    """
    Minimal, dependency-free wrapper around the Ollama /api/chat endpoint.

    Design principles:
    - Never crashes the FastAPI application.
    - Returns controlled IntelligenceResult on every error path.
    - Qwen output is advisory only — this service has no path to action executors.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        timeout: int = OLLAMA_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._chat_url = f"{self.base_url}/api/chat"

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Quick reachability check against /api/tags."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def analyze(
        self,
        investigation_context: dict[str, Any],
        case_id: str | None = None,
    ) -> IntelligenceResult:
        """
        Send investigation context to Qwen and return structured advisory intelligence.

        The investigation_context dict must be pre-sanitized by the caller
        (IntelligenceContextBuilder) — no credentials, tokens, or secrets.

        Returns IntelligenceResult with status in:
          ready       — successful analysis
          unavailable — Ollama not reachable
          timeout     — model call exceeded timeout
          error       — unexpected error
          no_data     — empty context
        """
        if not investigation_context:
            return IntelligenceResult(
                status="no_data",
                case_id=case_id,
                error_detail="Empty investigation context supplied.",
            )

        # 1. Check reachability first (fast-fail, avoids hanging)
        if not self.is_available():
            return IntelligenceResult(
                status="unavailable",
                case_id=case_id,
                error_detail="Ollama is not reachable at configured URL.",
            )

        # 2. Build user message from context
        user_message = self._build_user_message(investigation_context)

        # 3. Call the model
        try:
            raw_response = self._call_chat(user_message)
        except TimeoutError:
            return IntelligenceResult(
                status="timeout",
                case_id=case_id,
                error_detail=f"Ollama did not respond within {self.timeout}s.",
            )
        except urllib.error.URLError as exc:
            return IntelligenceResult(
                status="unavailable",
                case_id=case_id,
                error_detail=f"Network error: {exc}",
            )
        except Exception as exc:
            return IntelligenceResult(
                status="error",
                case_id=case_id,
                error_detail=f"Unexpected error: {exc}",
            )

        # 4. Parse and validate structured JSON output
        parsed = self._parse_response(raw_response, case_id)
        return parsed

    # ── PRIVATE ───────────────────────────────────────────────────────────────

    def _build_user_message(self, ctx: dict[str, Any]) -> str:
        """Convert investigation context dict to a compact, readable analyst briefing."""
        lines: list[str] = ["=== INVESTIGATION BRIEFING ==="]

        if ctx.get("case_id"):
            lines.append(f"Case ID: {ctx['case_id']}")
        if ctx.get("risk_level"):
            lines.append(f"Risk Level: {ctx['risk_level']}")
        if ctx.get("risk_score") is not None:
            lines.append(f"Risk Score: {ctx['risk_score']}/100")
        if ctx.get("topology_type"):
            lines.append(f"Network Topology: {ctx['topology_type']}")

        # Primary transaction
        pt = ctx.get("primary_transaction")
        if pt:
            lines.append("")
            lines.append("--- PRIMARY TRANSACTION ---")
            for k, v in pt.items():
                lines.append(f"  {k}: {v}")

        # Network summary
        ns = ctx.get("network_summary")
        if ns:
            lines.append("")
            lines.append("--- NETWORK SUMMARY ---")
            for k, v in ns.items():
                lines.append(f"  {k}: {v}")

        # Entities
        entities = ctx.get("entities", [])
        if entities:
            lines.append("")
            lines.append("--- KEY ENTITIES ---")
            for e in entities:
                lines.append(f"  {e}")

        # Transaction flows
        flows = ctx.get("transaction_flows", [])
        if flows:
            lines.append("")
            lines.append("--- TRANSACTION FLOWS ---")
            for f in flows:
                lines.append(f"  {f}")

        # Detected patterns
        patterns = ctx.get("detected_patterns", [])
        if patterns:
            lines.append("")
            lines.append("--- DETECTED PATTERNS ---")
            for p in patterns:
                lines.append(f"  {p}")

        # Policy decision (deterministic, already executed — context only)
        pd = ctx.get("policy_decision_summary")
        if pd:
            lines.append("")
            lines.append("--- DETERMINISTIC POLICY DECISION (context only) ---")
            lines.append(f"  {pd}")

        lines.append("")
        lines.append("Provide your structured JSON analysis of this investigation.")
        return "\n".join(lines)

    def _call_chat(self, user_message: str) -> str:
        """
        POST to /api/chat with non-streaming response.
        Raises TimeoutError on timeout, URLError on network issues.
        """
        payload = {
            "model": self.model,
            "stream": False,
            "options": {
                "temperature": 0.1,   # Low temperature for consistent, grounded analysis
                "num_predict": 1500,
            },
            "messages": [
                {"role": "system", "content": SENTINEL_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._chat_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except TimeoutError:
            raise
        except urllib.error.URLError:
            raise
        return raw

    def _parse_response(self, raw: str, case_id: str | None) -> IntelligenceResult:
        """
        Extract and validate the JSON analysis from Ollama's response envelope.
        Returns IntelligenceResult(status='error') on any parse failure.
        """
        try:
            ollama_resp = json.loads(raw)
        except json.JSONDecodeError as exc:
            return IntelligenceResult(
                status="error",
                case_id=case_id,
                error_detail=f"Invalid JSON from Ollama: {exc}",
            )

        # Ollama chat response: {"message": {"role": ..., "content": "..."}, ...}
        content: str = ""
        msg = ollama_resp.get("message") or {}
        if isinstance(msg, dict):
            content = msg.get("content", "")

        if not content:
            return IntelligenceResult(
                status="error",
                case_id=case_id,
                error_detail="Ollama returned empty message content.",
            )

        # Strip any <think>...</think> reasoning blocks generated by Qwen 3
        import re
        content_no_think = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

        # Strip markdown code fences if present
        stripped = content_no_think
        if "```" in stripped:
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', stripped, re.DOTALL)
            if match:
                stripped = match.group(1).strip()
            else:
                lines = [l for l in stripped.splitlines() if not l.strip().startswith("```")]
                stripped = "\n".join(lines).strip()

        # Fallback: find first '{' and last '}'
        if not stripped.startswith("{"):
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start != -1 and end != -1 and end > start:
                stripped = stripped[start:end+1]

        try:
            analysis_dict = json.loads(stripped)
        except json.JSONDecodeError as exc:
            return IntelligenceResult(
                status="error",
                case_id=case_id,
                error_detail=f"Model output is not valid JSON: {exc}. Raw: {stripped[:300]}",
            )

        try:
            analysis = AIAnalysisResponse(**analysis_dict)
        except Exception as exc:
            return IntelligenceResult(
                status="error",
                case_id=case_id,
                error_detail=f"Model output failed schema validation: {exc}",
            )

        return IntelligenceResult(
            status="ready",
            case_id=case_id,
            analysis=analysis,
        )


# ── SINGLETON ─────────────────────────────────────────────────────────────────
# Import this instance in routes — avoids repeated construction
ollama_service = OllamaService()
