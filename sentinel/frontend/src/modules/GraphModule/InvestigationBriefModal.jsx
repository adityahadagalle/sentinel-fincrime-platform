import React, { useState, useEffect } from 'react';
import { 
  X, Brain, Cpu, Shield, AlertTriangle, ChevronRight, ChevronDown, 
  GitCommit, Activity, FileText, CheckCircle2, ArrowRight, MapPin, Eye, Timer, WifiOff
} from 'lucide-react';

import AnalystEvidenceViewer from '../../components/AnalystEvidenceViewer';

const AI_STATUS = { IDLE: 'idle', LOADING: 'loading', READY: 'ready', UNAVAILABLE: 'unavailable', TIMEOUT: 'timeout', ERROR: 'error', NO_DATA: 'no_data' };

const InvestigationBriefModal = ({ caseData, onClose, onAnalyze, aiStatus, aiResult, aiError, onOpenReport }) => {
  const [expandedReport, setExpandedReport] = useState(null); // 'evidence' | 'contextual' | 'regulatory' | 'audit' | null
  const [stageData, setStageData] = useState(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Fetch Phase 1-4 stage reports if case ID present
  const [phase1Evidence, setPhase1Evidence] = useState(null);
  const [phase1Loading, setPhase1Loading] = useState(false);

  useEffect(() => {
    if (!caseData?.case_id) return;
    const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
    const cId = caseData.case_id;

    // Trigger or attach to backend investigation run
    fetch(`${API_BASE}/cases/${cId}/investigate?force_rerun=false`, { method: 'POST' })
      .then(res => res.ok ? res.json() : null)
      .then(run => {
        if (run) {
          fetch(`${API_BASE}/cases/${cId}/investigation`)
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (d) setStageData(d); })
            .catch(() => {});
        }
      })
      .catch(() => {});

    // Polling interval while investigation stages run
    const interval = setInterval(() => {
      fetch(`${API_BASE}/cases/${cId}/investigation`)
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data) {
            setStageData(data);
            const stages = data.stages || [];
            const allFinished = stages.length > 0 && stages.every(s => s.status === 'COMPLETED' || s.status === 'FAILED' || s.status === 'SKIPPED');
            if (allFinished) clearInterval(interval);
          }
        })
        .catch(() => {});
    }, 2000);

    setPhase1Loading(true);
    fetch(`${API_BASE}/cases/${cId}/evidence`)
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data) setPhase1Evidence(data); })
      .catch(() => {})
      .finally(() => setPhase1Loading(false));

    return () => clearInterval(interval);
  }, [caseData?.case_id]);

  if (!caseData) return null;

  const caseId = caseData.case_id || 'CASE-GENERAL';
  const riskScore = Number(caseData.risk_score || caseData.risk_level || 91);

  const analysis = aiResult?.analysis;
  const summary = analysis?.summary || '';
  const riskExplanation = analysis?.risk_explanation || '';
  const patterns = Array.isArray(analysis?.patterns) ? analysis.patterns : [];
  const networkExplanation = analysis?.network_explanation || '';
  const keyEntities = Array.isArray(analysis?.key_entities) ? analysis.key_entities : [];
  const recommendedSteps = Array.isArray(analysis?.recommended_investigation_steps) ? analysis.recommended_investigation_steps : [];
  const aiConfidence = analysis?.ai_confidence ?? 0;

  // Extract stage report objects
  const stagesList = Array.isArray(stageData?.stages) ? stageData.stages : [];
  const rawEvidenceStage = stagesList.find(s => s.stage === 'EVIDENCE')?.output;
  const evidenceStage = rawEvidenceStage || phase1Evidence;
  const contextualStage = stagesList.find(s => s.stage === 'CONTEXTUAL')?.output;
  const regulatoryStage = stagesList.find(s => s.stage === 'REGULATORY')?.output;
  const auditStage = stagesList.find(s => s.stage === 'AUDIT_EXPLANATION')?.output;
  const decisionSupportStage = stagesList.find(s => s.stage === 'DECISION_SUPPORT')?.output;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 select-none animate-fadeIn"
      style={{ background: 'rgba(2, 6, 23, 0.8)', backdropFilter: 'blur(10px)' }}
      onClick={() => onClose?.()}
    >
      <div
        className="relative w-full max-w-4xl bg-[#0F172A] border border-[#1E293B] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        style={{ color: '#F8FAFC', fontFamily: 'Hanken Grotesk, system-ui, sans-serif' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── HEADER ──────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1E293B] bg-[#0A0F17] shrink-0">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(56, 189, 248, 0.12)', border: '1px solid rgba(56, 189, 248, 0.35)' }}
            >
              <Brain className="w-5 h-5 text-sky-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold font-['JetBrains_Mono'] text-[#38BDF8] uppercase tracking-wider">
                  SENTINEL INTELLIGENCE BRIEF
                </span>
                <span className="text-[9px] font-['JetBrains_Mono'] px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-400 font-semibold">
                  LOCAL AI · QWEN 3:8B
                </span>
                <span className="text-[9px] font-['JetBrains_Mono'] px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 font-semibold">
                  ADVISORY INTELLIGENCE
                </span>
              </div>
              <div className="text-xs font-['JetBrains_Mono'] text-slate-400 mt-0.5 flex items-center gap-3">
                <span>Case: <strong className="text-slate-200">{caseId}</strong></span>
                <span>•</span>
                <span>Risk Score: <strong className="text-red-400">{riskScore}/100</strong></span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onAnalyze}
              disabled={aiStatus === AI_STATUS.LOADING}
              className="px-3 py-1.5 rounded-lg text-xs font-['JetBrains_Mono'] font-bold flex items-center gap-2 border transition-all disabled:opacity-50"
              style={{
                background: 'rgba(56, 189, 248, 0.1)',
                borderColor: 'rgba(56, 189, 248, 0.4)',
                color: '#38BDF8'
              }}
            >
              {aiStatus === AI_STATUS.LOADING ? <Cpu className="w-3.5 h-3.5 animate-spin" /> : <Brain className="w-3.5 h-3.5" />}
              {aiStatus === AI_STATUS.READY ? 'RE-RUN QWEN' : 'RUN QWEN BRIEF'}
            </button>

            <button
              onClick={() => onClose?.()}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-[#1E293B] transition-colors"
              title="Close Brief (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* ── BODY (SCROLLABLE) ───────────────────────────────────────────── */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">

          {/* STATUS NOTIFICATIONS */}
          {aiStatus === AI_STATUS.LOADING && (
            <div className="flex flex-col items-center justify-center py-10 gap-3 text-center border border-sky-500/20 bg-sky-500/5 rounded-xl font-['JetBrains_Mono']">
              <Cpu className="w-7 h-7 text-sky-400 animate-spin" />
              <div className="text-xs font-bold text-sky-400 uppercase">ANALYZING INVESTIGATION...</div>
              <div className="text-[11px] text-slate-400 max-w-md font-sans">
                Qwen 3:8B is synthesizing multi-hop graph topology, entity risk profiles, and transaction flows into structured advisory intelligence.
              </div>
            </div>
          )}

          {aiStatus === AI_STATUS.UNAVAILABLE && (
            <div className="flex flex-col items-center justify-center py-8 gap-2 text-center border border-[#1E293B] bg-[#060B15] rounded-xl font-['JetBrains_Mono']">
              <WifiOff className="w-6 h-6 text-slate-500" />
              <div className="text-xs font-bold text-slate-400 uppercase">OLLAMA UNAVAILABLE</div>
              <div className="text-[11px] text-slate-500 max-w-md font-sans">
                Ensure Ollama is running locally at http://localhost:11434 with the qwen3:8b model loaded.
              </div>
            </div>
          )}

          {aiStatus === AI_STATUS.TIMEOUT && (
            <div className="flex flex-col items-center justify-center py-8 gap-2 text-center border border-amber-500/30 bg-amber-500/5 rounded-xl font-['JetBrains_Mono']">
              <Timer className="w-6 h-6 text-amber-400" />
              <div className="text-xs font-bold text-amber-400 uppercase">ANALYSIS TIMEOUT</div>
              <div className="text-[11px] text-slate-400 max-w-md font-sans">
                Local Qwen inference timed out. Click RE-RUN QWEN above to retry.
              </div>
            </div>
          )}

          {aiStatus === AI_STATUS.NO_DATA && (
            <div className="flex flex-col items-center justify-center py-8 gap-2 text-center border border-[#1E293B] bg-[#060B15] rounded-xl font-['JetBrains_Mono']">
              <Shield className="w-6 h-6 text-slate-500" />
              <div className="text-xs font-bold text-slate-400 uppercase">NO DATA AVAILABLE</div>
              <div className="text-[11px] text-slate-500 font-sans">No investigation evidence found for this case ID.</div>
            </div>
          )}

          {aiStatus === AI_STATUS.ERROR && (
            <div className="flex flex-col items-center justify-center py-8 gap-2 text-center border border-rose-500/30 bg-rose-500/5 rounded-xl font-['JetBrains_Mono']">
              <AlertTriangle className="w-6 h-6 text-rose-400" />
              <div className="text-xs font-bold text-rose-400 uppercase">ANALYSIS ERROR</div>
              <div className="text-[11px] text-slate-400 max-w-md font-sans">{aiError || 'Failed to complete Qwen analysis.'}</div>
            </div>
          )}

          {aiStatus === AI_STATUS.READY && analysis && (
            <>
              {/* SECTION 1 — EXECUTIVE ASSESSMENT */}
              <div className="p-5 rounded-xl border border-[#1E293B] bg-[#060B15] space-y-2">
                <div className="text-[10px] font-['JetBrains_Mono'] font-bold text-sky-400 uppercase tracking-widest flex items-center justify-between">
                  <span>EXECUTIVE ASSESSMENT</span>
                  <span className="text-slate-500 font-normal">MODEL CONFIDENCE: {Math.round(aiConfidence * 100)}%</span>
                </div>
                <p className="text-xs text-slate-200 leading-relaxed font-['Hanken_Grotesk'] font-medium">
                  {summary}
                </p>
                {riskExplanation && (
                  <p className="text-[11px] text-slate-400 leading-relaxed pt-2 border-t border-[#1E293B]/60 font-sans">
                    <strong className="text-slate-300">Risk Rationale:</strong> {riskExplanation}
                  </p>
                )}
              </div>

              {/* SECTION 2 — PATTERN SIGNALS */}
              <div>
                <div className="text-[10px] font-['JetBrains_Mono'] font-bold text-slate-500 uppercase tracking-widest mb-2.5">
                  PATTERN SIGNALS
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {patterns.slice(0, 3).map((pat, i) => (
                    <div key={i} className="p-3.5 rounded-xl border border-[#1E293B] bg-[#060B15] space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-slate-200 truncate">{pat.name}</span>
                        <span className="text-[10px] font-['JetBrains_Mono'] font-bold text-sky-400">
                          {Math.round((pat.confidence || 0.8) * 100)}%
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed font-sans">
                        {pat.evidence}
                      </p>
                    </div>
                  ))}
                  {patterns.length === 0 && (
                    <div className="col-span-3 p-3 text-xs text-slate-500 text-center border border-[#1E293B] rounded-xl font-mono">
                      Standard multi-hop structuring signals detected.
                    </div>
                  )}
                </div>
              </div>

              {/* SECTION 3 — NETWORK FINDING */}
              {networkExplanation && (
                <div className="p-4 rounded-xl border border-[#1E293B] bg-[#060B15] flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="text-[10px] font-['JetBrains_Mono'] font-bold text-purple-400 uppercase tracking-widest flex items-center gap-1.5">
                      <GitCommit className="w-3.5 h-3.5" /> NETWORK INTELLIGENCE
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed font-sans italic">
                      "{networkExplanation}"
                    </p>
                  </div>
                  <button
                    onClick={() => onClose?.()}
                    className="px-3 py-1.5 rounded-lg text-xs font-['Hanken_Grotesk'] font-bold text-sky-400 hover:text-sky-300 transition-colors shrink-0 flex items-center gap-1.5"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    VIEW GRAPH →
                  </button>
                </div>
              )}

              {/* SECTION 4 — KEY ENTITIES */}
              {keyEntities.length > 0 && (
                <div>
                  <div className="text-[10px] font-['JetBrains_Mono'] font-bold text-slate-500 uppercase tracking-widest mb-2">
                    KEY ENTITIES RELEVANT TO INVESTIGATION
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {keyEntities.map((ent, i) => (
                      <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#1E293B] bg-[#060B15] font-['JetBrains_Mono'] text-xs">
                        <span className="text-sky-400 font-bold">{ent}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* SECTION 5 — RECOMMENDED NEXT STEPS */}
              {recommendedSteps.length > 0 && (
                <div>
                  <div className="text-[10px] font-['JetBrains_Mono'] font-bold text-amber-400 uppercase tracking-widest mb-2">
                    RECOMMENDED INVESTIGATION STEPS (ANALYST RECOMMENDATIONS)
                  </div>
                  <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 space-y-2">
                    {recommendedSteps.map((step, i) => (
                      <div key={i} className="flex items-start gap-2.5 text-xs text-slate-300 font-sans">
                        <span className="font-['JetBrains_Mono'] font-bold text-amber-400 shrink-0">{i + 1}.</span>
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* SECTION 6 — UPSTREAM AGENT EVIDENCE & TIMELINE */}
          <div className="pt-4 border-t border-[#1E293B]">
            <div className="text-[10px] font-['JetBrains_Mono'] font-bold text-slate-500 uppercase tracking-widest mb-3">
              UPSTREAM AGENT EVIDENCE TIMELINE
            </div>

            <div className="divide-y divide-[#1E293B]/60 border border-[#1E293B] rounded-xl bg-[#060B15] overflow-hidden">
              {[
                { num: '01', key: 'evidence', stage: 'EVIDENCE', title: 'Evidence Collection Agent', desc: 'Collect transaction, account and network evidence', data: evidenceStage, color: '#38BDF8' },
                { num: '02', key: 'contextual', stage: 'CONTEXTUAL', title: 'Contextual Investigation Agent', desc: 'Establish relationships and behavioral context', data: contextualStage, color: '#A78BFA' },
                { num: '03', key: 'regulatory', stage: 'REGULATORY', title: 'Regulatory Risk Assessment', desc: 'Assess regulatory and AML implications', data: regulatoryStage, color: '#F59E0B' },
                { num: '04', key: 'audit', stage: 'AUDIT_EXPLANATION', title: 'Audit Explanation Agent', desc: 'Build explainable investigation rationale', data: auditStage, color: '#34D399' },
                { num: '05', key: 'decision', stage: 'DECISION_SUPPORT', title: 'Analyst Decision Support', desc: 'Produce policy-ready investigation conclusion', data: decisionSupportStage, color: '#818CF8' },
              ].map(rep => {
                const isExpanded = expandedReport === rep.key;
                
                const computeStatus = () => {
                  if (rep.key === 'evidence') {
                    if (phase1Loading) return 'LOADING';
                    if (rep.data && (rep.data.evidence?.length > 0 || rep.data.summary?.total_evidence_items > 0)) return 'COMPLETED';
                    if (rep.data && rep.data.evidence?.length === 0) return 'NO DATA';
                  }
                  const stgObj = stagesList.find(s => s.stage === rep.stage);
                  if (stgObj?.status === 'COMPLETED' && rep.data) return 'COMPLETED';
                  if (stgObj?.status === 'FAILED') return 'FAILED';
                  if (stgObj?.status === 'RUNNING') return 'RUNNING';
                  return 'PENDING EXECUTION';
                };

                const currentStatus = computeStatus();
                const isCompleted = currentStatus === 'COMPLETED';

                return (
                  <div key={rep.key} className="p-4 space-y-2 transition-colors hover:bg-[#0A0F1D]/60">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="font-['JetBrains_Mono'] text-xs font-bold text-slate-500">{rep.num}</span>
                        <div>
                          <div className="font-['Hanken_Grotesk'] text-xs font-bold text-slate-200">{rep.title}</div>
                          <div className="text-[11px] text-slate-500">{rep.desc}</div>
                        </div>
                      </div>

                      <div className="flex items-center gap-4">
                        <span className={twMerge(
                          "text-[10px] font-['JetBrains_Mono'] font-bold flex items-center gap-1.5",
                          currentStatus === 'COMPLETED' ? "text-emerald-400" :
                          currentStatus === 'RUNNING' ? "text-sky-400 animate-pulse" :
                          currentStatus === 'FAILED' ? "text-rose-400" :
                          "text-slate-500"
                        )}>
                          <span>{currentStatus === 'COMPLETED' ? '●' : currentStatus === 'RUNNING' ? '◌' : currentStatus === 'FAILED' ? '●' : '○'}</span>
                          <span>{currentStatus}</span>
                        </span>

                        {isCompleted && (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => setExpandedReport(isExpanded ? null : rep.key)}
                              className="text-[11px] font-['Hanken_Grotesk'] font-medium text-slate-400 hover:text-slate-200 transition-colors"
                            >
                              {isExpanded ? 'COLLAPSE ↑' : 'DETAILS ↓'}
                            </button>
                            <button
                              onClick={() => onOpenReport?.(rep)}
                              className="text-[11px] font-['Hanken_Grotesk'] font-bold text-sky-400 hover:text-sky-300 transition-colors flex items-center gap-1"
                            >
                              VIEW REPORT →
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="pt-3 border-t border-[#1E293B]/40 mt-2">
                        <AnalystEvidenceViewer stageKey={rep.key} data={rep.data} status={currentStatus} title={rep.title} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── FOOTER ──────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-[#1E293B] bg-[#0A0F17] shrink-0">
          <div className="text-[10px] font-['JetBrains_Mono'] text-slate-500">
            ADVISORY INTELLIGENCE BRIEF · DETERMINISTIC POLICY ENGINE REMAINS AUTHORITATIVE
          </div>
          <button
            onClick={() => onClose?.()}
            className="px-4 py-1.5 rounded-lg text-xs font-['Hanken_Grotesk'] font-semibold bg-[#1E293B] hover:bg-[#334155] text-slate-200 transition-colors"
          >
            Close (Esc)
          </button>
        </div>
      </div>
    </div>
  );
};

export default InvestigationBriefModal;
