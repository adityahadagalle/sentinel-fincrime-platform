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

Your role is to synthesize and interpret supplied investigation reports (Evidence Collection, Contextual Investigation, Regulatory Risk Assessment, Audit Explanation, and Analyst Decision Support) and produce structured advisory intelligence for human compliance investigators.

CRITICAL ARCHITECTURAL CONSTRAINTS — READ CAREFULLY:
- The 5 investigation stages are deterministic system-generated findings. Your role is to synthesize and interpret those findings, NOT replace, fabricate, or contradict them.
- You are NOT the policy engine.
- You are NOT the action executor.
- You CANNOT freeze, block, reject, close, monitor, or otherwise modify any entity, account, or database state.
- You CANNOT override deterministic SENTINEL policy decisions.
- You CANNOT instruct any system to take autonomous enforcement action.
- Your output is ADVISORY INTELLIGENCE ONLY, intended for human compliance analysts.
- You MUST NOT invent transactions, accounts, amounts, entities, policies, or evidence not present in the supplied data.
- If certain investigation reports or stages are pending, running, or missing, explicitly state that and do not fabricate placeholders.
- Clearly distinguish between: (1) verified system findings from the 5 agents, (2) your AI synthesis and interpretation, (3) recommended manual investigation steps for human analysts.

ANALYST RESPONSIBILITIES:
- Synthesize the verified findings from all completed investigation stages into a cohesive case narrative.
- Explain why the case warrants investigation using concrete evidence from the supplied reports.
- Ground all identified patterns in specific agent evidence items, contextual rules, or regulatory triggers.
- Explain multi-hop transaction flows in clear, human-readable language.
- Identify key entities relevant to the investigation.
- Suggest concrete follow-up investigation steps for human analysts (NOT automated actions).
- Remain conservative when evidence or reports are incomplete — state missing information explicitly.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this exact schema:
{
  "summary": "<concise case synthesis of available agent findings, 2-3 sentences>",
  "risk_explanation": "<why this case warrants investigation, grounded in supplied reports>",
  "patterns": [
    {
      "name": "<pattern name>",
      "evidence": "<specific supporting evidence from agent reports or telemetry>",
      "confidence": <float 0.0 to 1.0>
    }
  ],
  "network_explanation": "<human-readable explanation of the transaction network flow>",
  "key_entities": ["<entity ID or description>"],
  "recommended_investigation_steps": ["<step for human analyst — NOT an automated action>"],
  "ai_confidence": <float 0.0 to 1.0>,
  "synthesized_stages": ["<list of stage names successfully synthesized, e.g. EVIDENCE, CONTEXTUAL>"],
  "missing_stages": ["<list of stage names pending, running, or missing at time of analysis>"]
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
    synthesized_stages: list[str] = Field(default_factory=list)
    missing_stages: list[str] = Field(default_factory=list)

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
    investigation_status: dict[str, str] = Field(default_factory=dict)
    synthesized_stages: list[str] = Field(default_factory=list)
    missing_stages: list[str] = Field(default_factory=list)
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

        inv_status = investigation_context.get("investigation_status", {})
        synth_stages = investigation_context.get("synthesized_stages", [])
        miss_stages = investigation_context.get("missing_stages", [])

        # 1. Check reachability first (fast-fail, avoids hanging)
        if not self.is_available():
            return IntelligenceResult(
                status="unavailable",
                case_id=case_id,
                investigation_status=inv_status,
                synthesized_stages=synth_stages,
                missing_stages=miss_stages,
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
                investigation_status=inv_status,
                synthesized_stages=synth_stages,
                missing_stages=miss_stages,
                error_detail=f"Ollama did not respond within {self.timeout}s.",
            )
        except urllib.error.URLError as exc:
            return IntelligenceResult(
                status="unavailable",
                case_id=case_id,
                investigation_status=inv_status,
                synthesized_stages=synth_stages,
                missing_stages=miss_stages,
                error_detail=f"Network error: {exc}",
            )
        except Exception as exc:
            return IntelligenceResult(
                status="error",
                case_id=case_id,
                investigation_status=inv_status,
                synthesized_stages=synth_stages,
                missing_stages=miss_stages,
                error_detail=f"Unexpected error: {exc}",
            )

        # 4. Parse and validate structured JSON output
        parsed = self._parse_response(raw_response, case_id, investigation_context)
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

        # ── 5-Stage Deterministic Investigation Status & Findings ─────────────
        inv_status = ctx.get("investigation_status", {})
        if inv_status:
            lines.append("")
            lines.append("--- 5-STAGE DETERMINISTIC INVESTIGATION STATUS ---")
            for stg_name, stg_state in inv_status.items():
                lines.append(f"  {stg_name.upper()}: {stg_state}")

        inv_reports = ctx.get("investigation_reports", {})
        if inv_reports:
            lines.append("")
            lines.append("--- 5-STAGE INVESTIGATION FINDINGS (VERIFIED SYSTEM REPORTS) ---")

            # Stage 1: Evidence Collection
            ev = inv_reports.get("evidence")
            if ev and isinstance(ev, dict):
                lines.append("")
                lines.append("[STAGE 1: EVIDENCE COLLECTION FINDINGS]")
                summary = ev.get("summary", {})
                lines.append(f"  Total Evidence Items: {summary.get('total_evidence_items', len(ev.get('evidence', [])))}")
                lines.append(f"  High Severity Items: {summary.get('high_severity_items', 0)}")
                lines.append(f"  Medium Severity Items: {summary.get('medium_severity_items', 0)}")
                if summary.get("categories_covered"):
                    lines.append(f"  Categories Covered: {', '.join(summary['categories_covered'])}")
                items = ev.get("evidence", [])
                for item in items[:10]:
                    it_id = item.get("id", "EV")
                    it_sev = item.get("severity", "INFO")
                    it_cat = item.get("category", "General")
                    it_finding = item.get("finding") or f"{item.get('indicator', '')} = {item.get('value', '')}"
                    it_src = item.get("source", "system")
                    lines.append(f"  - [{it_id}] [{it_sev}] {it_cat}: {it_finding} (Source: {it_src})")

            # Stage 2: Contextual Investigation
            ctx_rpt = inv_reports.get("contextual")
            if ctx_rpt and isinstance(ctx_rpt, dict):
                lines.append("")
                lines.append("[STAGE 2: CONTEXTUAL INVESTIGATION FINDINGS]")
                summary = ctx_rpt.get("summary", {})
                ctx_sev = summary.get("contextual_severity") or ctx_rpt.get("contextual_risk_level", "UNKNOWN")
                lines.append(f"  Contextual Severity: {ctx_sev}")
                lines.append(f"  Confidence: {summary.get('confidence', 1.0)}")
                patterns_list = ctx_rpt.get("patterns", ctx_rpt.get("patterns_detected", []))
                lines.append(f"  Patterns Detected: {len(patterns_list)}")
                for p in patterns_list:
                    p_name = p.get("name") or p.get("pattern_name", "Unknown")
                    p_desc = p.get("description") or p.get("reasoning", "")
                    p_sev = p.get("severity", "INFO")
                    p_conf = p.get("confidence", 1.0)
                    ev_ids = p.get("supporting_evidence_ids", [])
                    ev_str = f" [Evidence: {', '.join(ev_ids)}]" if ev_ids else ""
                    lines.append(f"  - {p_name} ({p_sev}, Conf: {p_conf}): {p_desc}{ev_str}")
                findings_list = ctx_rpt.get("contextual_findings", [])
                for f in findings_list[:5]:
                    lines.append(f"  - Finding: {f.get('finding')} (Severity: {f.get('severity', 'INFO')})")

            # Stage 3: Regulatory Risk Assessment
            reg_rpt = inv_reports.get("regulatory")
            if reg_rpt and isinstance(reg_rpt, dict):
                lines.append("")
                lines.append("[STAGE 3: REGULATORY RISK ASSESSMENT FINDINGS]")
                summary = reg_rpt.get("summary", {})
                lines.append(f"  Regulatory Severity: {summary.get('regulatory_severity', 'UNKNOWN')}")
                lines.append(f"  Assessment Heuristic Index: {summary.get('assessment_heuristic_index', 0.0)}")
                lines.append(f"  Jurisdiction Context: {summary.get('jurisdiction_context', 'INDIAN_FINANCIAL_SYSTEM_SIMULATION')}")
                indicators = reg_rpt.get("regulatory_indicators", [])
                for ind in indicators:
                    ind_id = ind.get("id", "REG")
                    ind_code = ind.get("code", "")
                    ind_desc = ind.get("description", "")
                    ind_sev = ind.get("severity", "INFO")
                    ind_impl = ind.get("reporting_implication", "MONITOR")
                    lines.append(f"  - [{ind_id}] {ind_code} ({ind_sev}): {ind_desc} [Implication: {ind_impl}]")
                considerations = reg_rpt.get("compliance_considerations", [])
                for c in considerations:
                    lines.append(f"  - Compliance Consideration [{c.get('code', 'CONSIDERATION')}]: {c.get('recommendation', '')}")

            # Stage 4: Audit Explanation
            aud_rpt = inv_reports.get("audit_explanation")
            if aud_rpt and isinstance(aud_rpt, dict):
                lines.append("")
                lines.append("[STAGE 4: AUDIT EXPLANATION FINDINGS]")
                if aud_rpt.get("executive_summary"):
                    lines.append(f"  Executive Summary: {aud_rpt['executive_summary']}")
                summary = aud_rpt.get("summary", {})
                if summary.get("traceability_status"):
                    lines.append(f"  Traceability Status: {summary['traceability_status']}")
                narrative = aud_rpt.get("investigation_narrative", [])
                for step in narrative:
                    lines.append(f"  - Step {step.get('step_number', '')}: {step.get('title', '')} — {step.get('description', '')}")
                key_findings = aud_rpt.get("key_findings", [])
                for kf in key_findings:
                    lines.append(f"  - Key Finding [{kf.get('finding_id', 'KF')}]: {kf.get('statement', '')} (Severity: {kf.get('severity', 'INFO')})")
                uncertainties = aud_rpt.get("uncertainties", [])
                if uncertainties:
                    lines.append(f"  Uncertainties: {'; '.join(uncertainties)}")
                data_gaps = aud_rpt.get("data_gaps", [])
                if data_gaps:
                    lines.append(f"  Data Gaps: {'; '.join(data_gaps)}")

            # Stage 5: Decision Support
            ds_rpt = inv_reports.get("decision_support")
            if ds_rpt and isinstance(ds_rpt, dict):
                lines.append("")
                lines.append("[STAGE 5: ANALYST DECISION SUPPORT FINDINGS]")
                summary = ds_rpt.get("summary", {})
                prio = ds_rpt.get("review_priority") or summary.get("review_priority", "UNKNOWN")
                lines.append(f"  Operational Review Priority: {prio}")
                if ds_rpt.get("priority_rationale"):
                    lines.append(f"  Priority Rationale: {ds_rpt['priority_rationale']}")
                if ds_rpt.get("analyst_executive_brief"):
                    lines.append(f"  Analyst Executive Brief: {ds_rpt['analyst_executive_brief']}")
                review_steps = ds_rpt.get("recommended_review_steps", [])
                for st in review_steps:
                    lines.append(f"  - Recommended Step [{st.get('step_id', '')}]: {st.get('action', '')} (Priority: {st.get('priority', '')}) — {st.get('rationale', '')}")
                dispositions = ds_rpt.get("disposition_options", [])
                for disp in dispositions:
                    rec_flag = " [RECOMMENDED]" if disp.get("recommended") else ""
                    lines.append(f"  - Disposition Option: {disp.get('label', '')} ({disp.get('action_code', '')}){rec_flag} — {disp.get('description', '')}")
                boundary = ds_rpt.get("human_approval_boundary", {})
                lines.append(f"  Human Approval Boundary: Autonomous Execution = {boundary.get('autonomous_execution', False)}, Required Role = {boundary.get('required_role', 'COMPLIANCE_ANALYST')}")

        # Incomplete / missing stages
        all_stage_names = ["EVIDENCE", "CONTEXTUAL", "REGULATORY", "AUDIT_EXPLANATION", "DECISION_SUPPORT"]
        missing = [s for s in all_stage_names if inv_status.get(s.lower()) != "COMPLETED" or s.lower() not in inv_reports]
        if missing:
            lines.append("")
            lines.append("--- INCOMPLETE / PENDING / MISSING INVESTIGATION STAGES ---")
            for m in missing:
                st = inv_status.get(m.lower(), "NOT_STARTED")
                lines.append(f"  [STAGE: {m}] Stage NOT COMPLETED (Status: {st}). No verified findings available. Do NOT speculate, infer, or fabricate findings for this stage.")

        # Policy decision (deterministic, already executed — context only)
        pd = ctx.get("policy_decision_summary")
        if pd:
            lines.append("")
            lines.append("--- DETERMINISTIC POLICY DECISION (context only) ---")
            lines.append(f"  {pd}")

        lines.append("")
        lines.append("Provide your structured JSON analysis synthesizing this investigation.")
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

    def _parse_response(self, raw: str, case_id: str | None, ctx: dict[str, Any] | None = None) -> IntelligenceResult:
        """
        Extract and validate the JSON analysis from Ollama's response envelope.
        Returns IntelligenceResult(status='error') on any parse failure.
        """
        inv_status = ctx.get("investigation_status", {}) if ctx else {}
        inv_reports = ctx.get("investigation_reports", {}) if ctx else {}
        completed_stages = [
            s.upper() for s, st in inv_status.items() 
            if st == "COMPLETED" and s in inv_reports
        ]
        pending_stages = [
            s.upper() for s, st in inv_status.items() 
            if st != "COMPLETED" or s not in inv_reports
        ]

        try:
            ollama_resp = json.loads(raw)
        except json.JSONDecodeError as exc:
            return IntelligenceResult(
                status="error",
                case_id=case_id,
                investigation_status=inv_status,
                synthesized_stages=completed_stages,
                missing_stages=pending_stages,
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
                investigation_status=inv_status,
                synthesized_stages=completed_stages,
                missing_stages=pending_stages,
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
                investigation_status=inv_status,
                synthesized_stages=completed_stages,
                missing_stages=pending_stages,
                error_detail=f"Model output is not valid JSON: {exc}. Raw: {stripped[:300]}",
            )

        # Populate synthesized / missing stages if model omitted them
        if "synthesized_stages" not in analysis_dict or not analysis_dict["synthesized_stages"]:
            analysis_dict["synthesized_stages"] = completed_stages
        if "missing_stages" not in analysis_dict or not analysis_dict["missing_stages"]:
            analysis_dict["missing_stages"] = pending_stages

        try:
            analysis = AIAnalysisResponse(**analysis_dict)
        except Exception as exc:
            return IntelligenceResult(
                status="error",
                case_id=case_id,
                investigation_status=inv_status,
                synthesized_stages=completed_stages,
                missing_stages=pending_stages,
                error_detail=f"Model output failed schema validation: {exc}",
            )

        return IntelligenceResult(
            status="ready",
            case_id=case_id,
            analysis=analysis,
            investigation_status=inv_status,
            synthesized_stages=analysis.synthesized_stages,
            missing_stages=analysis.missing_stages,
        )


# ── SINGLETON ─────────────────────────────────────────────────────────────────
# Import this instance in routes — avoids repeated construction
ollama_service = OllamaService()
