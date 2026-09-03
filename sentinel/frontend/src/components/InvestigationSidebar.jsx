import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import RiskBadge from './RiskBadge';
import GoldenTimer from './GoldenTimer';
import { maskAccount } from '../utils/maskAccount';
import { twMerge } from 'tailwind-merge';
import { X, ShieldAlert, Activity, ArrowRight, Clock, Lock, CheckCircle2, AlertTriangle, GitCommit, FileText, ChevronRight, ChevronDown, Zap, Network } from 'lucide-react';
import AnalystEvidenceViewer from './AnalystEvidenceViewer';

const InvestigationSidebar = ({ 
  isOpen, 
  selectedCase, 
  selectedTransaction, 
  actions = [], 
  onClose,
  role,
  isAutomationOn = true
}) => {
  const navigate = useNavigate();
  const isViewer = role !== 'admin';
  const [expandedPhase, setExpandedPhase] = useState(null);
  const [investigationReadModel, setInvestigationReadModel] = useState(null);
  const [phase1Evidence, setPhase1Evidence] = useState(null);
  const [phase1Loading, setPhase1Loading] = useState(false);

  const [isAccountFrozen, setIsAccountFrozen] = useState(selectedCase?.status === 'FROZEN' || selectedTransaction?.status === 'FROZEN');
  const [freezeError, setFreezeError] = useState(null);
  const [freezeLoading, setFreezeLoading] = useState(false);

  React.useEffect(() => {
    if (selectedCase?.status === 'FROZEN' || selectedTransaction?.status === 'FROZEN') {
      setIsAccountFrozen(true);
    }
  }, [selectedCase?.status, selectedTransaction?.status]);

  React.useEffect(() => {
    if (!isOpen) return;
    const targetId = selectedCase?.case_id || selectedTransaction?.case_id;
    if (!targetId) return;
    const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

    // Trigger or attach to backend investigation run
    fetch(`${API_BASE}/cases/${targetId}/investigate?force_rerun=false`, { method: 'POST' })
      .then(res => res.ok ? res.json() : null)
      .then(run => {
        if (run) {
          fetch(`${API_BASE}/cases/${targetId}/investigation`)
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (d) setInvestigationReadModel(d); })
            .catch(() => {});
        }
      })
      .catch(() => {});

    // Polling interval while investigation stages run
    const interval = setInterval(() => {
      fetch(`${API_BASE}/cases/${targetId}/investigation`)
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data) {
            setInvestigationReadModel(data);
            const stages = data.stages || [];
            const allFinished = stages.length > 0 && stages.every(s => s.status === 'COMPLETED' || s.status === 'FAILED' || s.status === 'SKIPPED');
            if (allFinished) clearInterval(interval);
          }
        })
        .catch(() => {});
    }, 2000);

    setPhase1Loading(true);
    fetch(`${API_BASE}/cases/${targetId}/evidence`)
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data) setPhase1Evidence(data); })
      .catch(() => {})
      .finally(() => setPhase1Loading(false));

    return () => clearInterval(interval);
  }, [isOpen, selectedCase?.case_id, selectedTransaction?.case_id]);

  if (!isOpen) return null;

  const caseId = selectedCase?.case_id || selectedTransaction?.case_id || selectedTransaction?.tx_id || 'CASE-ATTACK-001';
  const riskScore = Number(selectedCase?.risk_level || selectedTransaction?.risk_score || 91);
  const totalFraud = selectedCase?.total_fraud_amount || selectedTransaction?.amount || 120000;
  const recoverable = selectedCase?.recoverable_amount || Math.round(totalFraud * 0.8);
  const status = isAccountFrozen ? 'FROZEN' : (selectedCase?.status || 'HIGH_RISK');
  const isSuspicious = riskScore >= 60 || status === 'HIGH_RISK' || isAccountFrozen;

  const txId = selectedTransaction?.tx_id || selectedCase?.primary_tx_id || 'TX-27678ED4';
  const amount = Number(selectedTransaction?.amount || totalFraud || 62967.87);
  const channel = selectedTransaction?.channel || 'UPI';
  const sender = selectedTransaction?.sender_account || 'ACC-USR-8122';
  const receiver = selectedTransaction?.receiver_account || 'ACC-MERCH-2062';

  const handleAction = async (actionEndpoint) => {
    const targetCaseId = selectedCase?.case_id || selectedTransaction?.case_id || selectedTransaction?.tx_id;
    if (!targetCaseId) return;
    const targetAccount = selectedTransaction?.receiver_account || "GLOBAL";
    
    if (actionEndpoint === 'freeze') {
      setFreezeLoading(true);
      setFreezeError(null);
    }

    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${API_BASE}/action/${actionEndpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_id: targetCaseId,
          target_id: txId,
          account_id: targetAccount,
          reason: `Action ${actionEndpoint} executed by human operator`,
          operator_id: "OPERATOR_ADMIN"
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (actionEndpoint === 'freeze' && (data.action_status === 'SUCCESS' || data.execution_status === 'SUCCESS' || data.status === 'FROZEN' || data.action_executed)) {
          setIsAccountFrozen(true);
          setFreezeError(null);
        } else if (actionEndpoint === 'freeze') {
          setFreezeError(data.detail || 'FREEZE FAILED — Unable to confirm account state change.');
        }
      } else if (actionEndpoint === 'freeze') {
        const errDetail = await res.json().catch(() => null);
        console.error(`[Freeze Action] HTTP ${res.status}:`, errDetail);
        setFreezeError(errDetail?.detail || `FREEZE FAILED (HTTP ${res.status}) — Unable to confirm account state change.`);
      }
    } catch (error) {
      console.error('Network error during action execution:', error);
      if (actionEndpoint === 'freeze') {
        setFreezeError('FREEZE FAILED — Network error while contacting backend.');
      }
    } finally {
      if (actionEndpoint === 'freeze') setFreezeLoading(false);
    }
  };

  // Upstream agent stage outputs for progressive disclosure
  const stagesList = Array.isArray(investigationReadModel?.stages) ? investigationReadModel.stages : [];
  const rawEvidenceStage = stagesList.find(s => s.stage === 'EVIDENCE')?.output;
  const evidenceStage = rawEvidenceStage || phase1Evidence;
  const contextualStage = stagesList.find(s => s.stage === 'CONTEXTUAL')?.output;
  const regulatoryStage = stagesList.find(s => s.stage === 'REGULATORY')?.output;
  const auditStage = stagesList.find(s => s.stage === 'AUDIT_EXPLANATION')?.output;
  const decisionSupportStage = stagesList.find(s => s.stage === 'DECISION_SUPPORT')?.output;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 select-none font-sans animate-fadeIn">
      {/* Translucent Backdrop */}
      <div 
        className="fixed inset-0 bg-black/80 backdrop-blur-md transition-opacity" 
        onClick={onClose}
      />

      {/* Centered Workstation Modal Container */}
      <div className="relative w-full max-w-5xl bg-[#0A0F1D]/95 border border-sky-500/20 rounded-2xl shadow-[0_0_50px_rgba(56,189,248,0.12)] overflow-hidden max-h-[88vh] flex flex-col my-auto z-10">
        
        {/* ── 1. HEADER ─────────────────────────────────────────────────────── */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-[#1E293B] bg-[#060B15] shrink-0">
          <div className="flex items-center gap-3.5">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{
                background: isSuspicious ? 'rgba(239, 68, 68, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                border: `1px solid ${isSuspicious ? 'rgba(239, 68, 68, 0.4)' : 'rgba(56, 189, 248, 0.4)'}`
              }}
            >
              {isSuspicious ? <ShieldAlert className="w-5 h-5 text-red-400" /> : <Activity className="w-5 h-5 text-sky-400" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                  INVESTIGATION WORKSTATION
                </span>
                <span className="text-[10px] font-mono text-slate-500">
                  CASE: {caseId}
                </span>
              </div>
              <h2 className="text-lg font-mono font-bold text-[#38BDF8]">
                {txId}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                onClose();
                const effCaseId = caseId || selectedCase?.case_id || 'CASE-' + String(txId || '').slice(-8);
                navigate(`/graph/${effCaseId}?tx=${txId}`);
              }}
              className="px-3 py-1 rounded bg-sky-500/20 border border-sky-500/40 hover:bg-sky-500/30 text-sky-300 font-mono text-[11px] font-bold transition-all flex items-center gap-1.5 shadow-sm"
              title="Open Investigation Graph centered on this transaction"
            >
              <Network className="w-3.5 h-3.5" />
              <span>Open Graph</span>
            </button>
            <RiskBadge score={riskScore} />
            {selectedCase?.golden_window_minutes && (
              <GoldenTimer minutes={selectedCase.golden_window_minutes} />
            )}
            <span className={twMerge(
              "text-[10px] font-mono font-bold px-2.5 py-1 rounded border uppercase tracking-wider",
              status === 'HIGH_RISK' ? "bg-rose-950 text-rose-300 border-rose-800" : "bg-slate-800 text-slate-300 border-slate-700"
            )}>
              STATUS: {status}
            </span>
            <button 
              onClick={onClose} 
              className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-slate-200"
              title="Close (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </header>

        {/* ── 2. PRIMARY METRIC STRIP ───────────────────────────────────────── */}
        <div className="grid grid-cols-4 divide-x divide-[#1E293B] border-b border-[#1E293B] bg-[#0A0F1D] shrink-0 text-xs font-mono">
          <div className="p-4">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">RISK ASSESSMENT</div>
            <div className="text-sm font-bold text-red-400 mt-0.5">{riskScore} / 100</div>
            <div className="text-[9px] text-red-400/80 font-bold uppercase">CRITICAL PRIORITY</div>
          </div>

          <div className="p-4">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">TOTAL FRAUD VALUE</div>
            <div className="text-base font-bold text-emerald-400 mt-0.5">₹{amount.toLocaleString('en-IN')}</div>
            <div className="text-[9px] text-slate-400">{channel} CHANNEL</div>
          </div>

          <div className="p-4">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">RECOVERABLE AMOUNT</div>
            <div className="text-base font-bold text-emerald-400 mt-0.5">₹{recoverable.toLocaleString('en-IN')}</div>
            <div className="text-[9px] text-emerald-400/80 font-bold">ESTIMATED RECOVERY</div>
          </div>

          <div className="p-4">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">HOP POSITION</div>
            <div className="text-sm font-bold text-sky-400 mt-0.5">HOP 2 OF 5</div>
            <div className="text-[9px] text-slate-400">IN MULTI-HOP FLOW</div>
          </div>
        </div>

        {/* ── 3. TWO-COLUMN WORKSPACE BODY ──────────────────────────────────── */}
        <div className="p-6 grid grid-cols-2 gap-6 overflow-y-auto flex-1 text-xs">

          {/* LEFT COLUMN: TRANSACTION FLOW & NETWORK CONTEXT */}
          <div className="space-y-5">
            {/* Money Movement Flow Card */}
            <div className="p-4 rounded-xl border border-[#1E293B] bg-[#060B15] space-y-3">
              <div className="text-[10px] font-mono font-bold text-sky-400 uppercase tracking-widest flex items-center justify-between">
                <span>MONEY MOVEMENT FLOW</span>
                <span className="text-[9px] text-slate-500 font-normal">CHANNEL: {channel}</span>
              </div>

              <div className="flex items-center justify-between gap-3 pt-1">
                <div className="flex-1 bg-[#0A0F1D] p-3 rounded-lg border border-[#1E293B]">
                  <span className="text-[9px] text-slate-500 uppercase block mb-0.5">SENDER</span>
                  <span className="font-mono text-xs font-bold text-slate-100 block truncate">
                    {isViewer ? maskAccount(sender) : sender}
                  </span>
                  <span className="text-[9px] text-slate-500">VICTIM</span>
                </div>

                <div className="flex flex-col items-center shrink-0 px-2 text-center">
                  <span className="font-mono text-xs font-bold text-emerald-400">₹{amount.toLocaleString('en-IN')}</span>
                  <div className="flex items-center gap-1 my-1">
                    <div className="w-8 h-0.5 bg-gradient-to-r from-sky-500 to-emerald-400 animate-pulse" />
                    <ArrowRight className="w-4 h-4 text-emerald-400 shrink-0" />
                  </div>
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-sky-300 border border-slate-700">
                    Hop 2/5
                  </span>
                </div>

                <div className={twMerge(
                  "flex-1 p-3 rounded-lg border",
                  isAccountFrozen ? "bg-rose-950/20 border-rose-500/40" : "bg-[#0A0F1D] border-[#1E293B]"
                )}>
                  <span className="text-[9px] text-slate-500 uppercase block mb-0.5">RECEIVER</span>
                  <span className="font-mono text-xs font-bold text-slate-100 block truncate">
                    {isViewer ? maskAccount(receiver) : receiver}
                  </span>
                  {isAccountFrozen ? (
                    <span className="text-[9px] text-rose-400 font-bold flex items-center gap-1 mt-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500" /> ACCOUNT STATE: FROZEN
                    </span>
                  ) : (
                    <span className="text-[9px] text-purple-400 font-semibold">MULE RECEIVER</span>
                  )}
                </div>
              </div>
            </div>

            {/* Network Context */}
            <div className="p-4 rounded-xl border border-[#1E293B] bg-[#060B15] space-y-3">
              <div className="text-[10px] font-mono font-bold text-purple-400 uppercase tracking-widest flex items-center gap-1.5">
                <GitCommit className="w-3.5 h-3.5" /> NETWORK CONTEXT
              </div>

              <div className="grid grid-cols-2 gap-3 font-mono">
                <div className="p-2.5 rounded bg-[#0A0F1D] border border-[#1E293B]">
                  <span className="text-[9px] text-slate-500 uppercase block">PATTERN TYPE</span>
                  <span className="font-semibold text-purple-300 mt-0.5 block">MULE CHAIN LAYERED</span>
                </div>

                <div className="p-2.5 rounded bg-[#0A0F1D] border border-[#1E293B]">
                  <span className="text-[9px] text-slate-500 uppercase block">CHAIN ID</span>
                  <span className="font-semibold text-sky-300 mt-0.5 block truncate">CHAIN-0921</span>
                </div>
              </div>
            </div>

            {/* UPSTREAM AGENT EVIDENCE & TIMELINE */}
            <div className="pt-2">
              <div className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest mb-2">
                UPSTREAM AGENT EVIDENCE TIMELINE
              </div>
              <div className="divide-y divide-[#1E293B]/60 border border-[#1E293B] rounded-xl bg-[#060B15] overflow-hidden">
                {[
                  { num: '01', key: 'evidence', stage: 'EVIDENCE', title: 'Evidence Collection Agent', desc: 'Collect transaction, account and network evidence', data: evidenceStage, color: '#38BDF8' },
                  { num: '02', key: 'contextual', stage: 'CONTEXTUAL', title: 'Contextual Investigation Agent', desc: 'Establish relationships and behavioral context', data: contextualStage, color: '#A78BFA' },
                  { num: '03', key: 'regulatory', stage: 'REGULATORY', title: 'Regulatory Risk Assessment', desc: 'Assess regulatory and AML implications', data: regulatoryStage, color: '#F59E0B' },
                  { num: '04', key: 'audit', stage: 'AUDIT_EXPLANATION', title: 'Audit Explanation Agent', desc: 'Build explainable investigation rationale', data: auditStage, color: '#34D399' },
                  { num: '05', key: 'decision', stage: 'DECISION_SUPPORT', title: 'Analyst Decision Support', desc: 'Produce policy-ready investigation conclusion', data: decisionSupportStage, color: '#818CF8' },
                ].map((ph) => {
                  const isExpanded = expandedPhase === ph.key;

                  const computeStatus = () => {
                    if (ph.key === 'evidence') {
                      if (phase1Loading) return 'LOADING';
                      if (ph.data && (ph.data.evidence?.length > 0 || ph.data.summary?.total_evidence_items > 0)) return 'COMPLETED';
                      if (ph.data && ph.data.evidence?.length === 0) return 'NO DATA';
                    }
                    const stgObj = stagesList.find(s => s.stage === ph.stage);
                    if (stgObj?.status === 'COMPLETED' && ph.data) return 'COMPLETED';
                    if (stgObj?.status === 'FAILED') return 'FAILED';
                    if (stgObj?.status === 'RUNNING') return 'RUNNING';
                    return 'PENDING EXECUTION';
                  };

                  const currentStatus = computeStatus();
                  const isCompleted = currentStatus === 'COMPLETED';

                  return (
                    <div key={ph.key} className="p-3 space-y-1.5 transition-colors hover:bg-[#0A0F1D]/60">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <span className="font-mono text-[11px] font-bold text-slate-500">{ph.num}</span>
                          <div>
                            <div className="font-sans text-xs font-bold text-slate-200">{ph.title}</div>
                            <div className="text-[10px] text-slate-500 font-sans">{ph.desc}</div>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          <span className={twMerge(
                            "text-[9px] font-mono font-bold flex items-center gap-1",
                            currentStatus === 'COMPLETED' ? "text-emerald-400" :
                            currentStatus === 'RUNNING' ? "text-sky-400 animate-pulse" :
                            currentStatus === 'FAILED' ? "text-rose-400" :
                            "text-slate-500"
                          )}>
                            <span>{currentStatus === 'COMPLETED' ? '●' : currentStatus === 'RUNNING' ? '◌' : currentStatus === 'FAILED' ? '●' : '○'}</span>
                            <span>{currentStatus}</span>
                          </span>

                          {isCompleted && (
                            <button
                              onClick={() => setExpandedPhase(isExpanded ? null : ph.key)}
                              className="text-[10px] font-mono font-semibold text-sky-400 hover:text-sky-300 transition-colors"
                            >
                              {isExpanded ? 'COLLAPSE ↑' : 'VIEW REPORT →'}
                            </button>
                          )}
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="pt-2 border-t border-[#1E293B]/40 mt-1.5">
                          <AnalystEvidenceViewer stageKey={ph.key} data={ph.data} status={currentStatus} title={ph.title} />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: KEY RISK SIGNALS & WHY THIS MATTERS */}
          <div className="space-y-5">
            {/* Key Risk Signals */}
            <div>
              <div className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest mb-2.5">
                KEY RISK SIGNALS
              </div>
              <div className="space-y-2.5">
                {[
                  { title: 'NEW RECEIVER OBSERVED', desc: 'First recorded transfer to destination account within 30-day velocity window.', score: '+35 Risk' },
                  { title: 'AMOUNT DEVIATION', desc: `Transfer of ₹${amount.toLocaleString('en-IN')} is 63% above baseline transaction size.`, score: '+25 Risk' },
                  { title: 'MULTI-HOP PASS-THROUGH', desc: 'Rapid layered routing detected at Hop 2 of 5 in active mule chain.', score: '+18 Risk' }
                ].map((sig, i) => (
                  <div key={i} className="p-3 rounded-xl border border-red-500/20 bg-[#060B15]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                        {sig.title}
                      </span>
                      <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/30">
                        {sig.score}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      {sig.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Why This Matters */}
            <div className="p-4 rounded-xl border border-sky-500/20 bg-sky-500/5 space-y-1.5">
              <div className="text-[10px] font-mono font-bold text-sky-400 uppercase tracking-widest flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5" /> WHY THIS TRANSACTION MATTERS
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                "This transaction is part of a high-risk multi-hop fund flow involving a newly observed receiver and abnormal transaction behavior. Its position at Hop 2 of 5 within the active mule chain increases investigative relevance."
              </p>
            </div>
          </div>
        </div>

        {/* ── 4. FOOTER: AUTOMATION STATUS & OPERATOR FREEZE CONTROL ──────── */}
        <footer className="px-6 py-4 border-t border-[#1E293B] bg-[#060B15] shrink-0 flex items-center justify-between">
          {/* Automation Active Indicator */}
          {isAutomationOn ? (
            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span className="font-bold text-emerald-400">AUTOMATION ACTIVE</span>
              <span className="text-slate-600">·</span>
              <span className="text-slate-500">NON-FREEZE ACTIONS EXECUTED AUTONOMOUSLY BY POLICY ENGINE</span>
            </div>
          ) : (
            <div className="text-xs font-mono text-amber-400 font-bold">
              MANUAL OPERATOR MODE
            </div>
          )}

          {/* Action Controls: FREEZE / PERSISTENT FROZEN STATE */}
          <div className="flex items-center gap-3">
            {freezeError && (
              <span className="text-xs font-mono text-rose-400 font-bold">
                ⚠ {freezeError}
              </span>
            )}

            {isAccountFrozen ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 text-xs font-mono">
                <span className="w-2 h-2 rounded-full bg-rose-400" />
                <span className="font-bold text-rose-400">ACCOUNT FROZEN</span>
                <span className="text-slate-600">·</span>
                <span className="text-slate-400">Action completed by Human Operator</span>
              </div>
            ) : isSuspicious && (
              <button
                onClick={() => handleAction('freeze')}
                disabled={isViewer || freezeLoading}
                className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-rose-600 hover:bg-rose-500 text-white border border-rose-400 shadow-lg transition-all flex items-center gap-2 disabled:opacity-40"
              >
                <Lock className="w-3.5 h-3.5" />
                <span>{freezeLoading ? 'PERSISTING FREEZE...' : 'FREEZE ACCOUNT'}</span>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-black/30 text-rose-200">HUMAN OPERATOR APPROVAL REQUIRED</span>
              </button>
            )}

            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-[#1E293B] hover:bg-[#334155] text-slate-200 transition-colors"
            >
              Close (Esc)
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default InvestigationSidebar;
