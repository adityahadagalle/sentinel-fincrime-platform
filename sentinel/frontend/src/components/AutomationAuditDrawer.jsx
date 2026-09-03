import React from 'react';
import { X, ShieldCheck, Lock, Activity, Bot, FileText, CheckCircle2, Clock, UserCheck } from 'lucide-react';

const AutomationAuditDrawer = ({ auditData, onClose }) => {
  if (!auditData) return null;

  const rec = auditData.execution_record || auditData.automation_execution || auditData;
  const isRestricted = rec.requires_human_approval || rec.action_status === 'REQUIRES_HUMAN_APPROVAL';

  return (
    <div className="fixed inset-y-0 right-0 z-[130] w-full max-w-xl bg-slate-950/95 border-l border-slate-800 backdrop-blur-2xl shadow-2xl flex flex-col font-sans select-none animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-sky-500/20 text-sky-400 rounded-xl border border-sky-500/30">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold font-mono text-slate-100 uppercase tracking-wide">
              AUTOMATION AUDIT TRAIL
            </h3>
            <span className="text-[11px] font-mono text-slate-400">
              Transaction: {rec.transaction_id || rec.tx_id || 'UNKNOWN'}
            </span>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5 text-xs">
        {/* Status Banner */}
        <div
          className={`p-4 rounded-xl border flex items-center justify-between ${
            isRestricted
              ? 'bg-amber-950/40 border-amber-500/40 text-amber-300'
              : 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
          }`}
        >
          <div className="space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
              EXECUTION DECISION
            </div>
            <div className="font-mono font-bold text-sm uppercase flex items-center gap-2">
              {isRestricted ? <Lock className="w-4 h-4 text-amber-400" /> : <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
              {rec.action_status || 'EXECUTED'}
            </div>
          </div>

          <div className="text-right space-y-1 font-mono">
            <div className="text-[10px] text-slate-400 uppercase">MODE</div>
            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-800 border border-slate-700 text-slate-200">
              {rec.mode || 'AUTOMATE_ON'}
            </span>
          </div>
        </div>

        {/* 16-Step Decision Trail Timeline */}
        <div className="space-y-3">
          <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-2">
            16-FIELD DECISION & GOVERNANCE TRAIL
          </h4>

          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">1. Transaction ID</span>
              <span className="font-mono font-bold text-slate-200">{rec.transaction_id || rec.tx_id}</span>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">2. Associated Case ID</span>
              <span className="font-mono font-bold text-slate-200">{rec.case_id || 'CASE-UNASSIGNED'}</span>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">3. Risk Score</span>
              <span className="font-mono font-bold text-slate-100">{rec.risk_score}</span>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">4. Risk Level</span>
              <span className="font-mono font-bold text-rose-400">{rec.risk_level}</span>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">5. Selected Action</span>
              <span className="font-mono font-bold text-sky-400">{rec.action}</span>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">6. Governance Check</span>
              <span className={`font-mono font-bold ${isRestricted ? 'text-amber-400' : 'text-emerald-400'}`}>
                {isRestricted ? 'INTERCEPTED' : 'PASSED'}
              </span>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">7. Execution Result</span>
              <span className="font-mono font-bold text-slate-200">{rec.execution_result}</span>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">8. Human Approval</span>
              <span className={`font-mono font-bold ${rec.requires_human_approval ? 'text-amber-400' : 'text-slate-400'}`}>
                {rec.requires_human_approval ? 'REQUIRED' : 'NOT REQUIRED'}
              </span>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 col-span-2">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">9. Decision Factors / Signals</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {(rec.decision_factors || ['standard_rules']).map((f) => (
                  <span key={f} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px] border border-slate-700">
                    {f}
                  </span>
                ))}
              </div>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 col-span-2">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">10. Policy Rationale</span>
              <p className="text-slate-300 text-[11px] leading-relaxed mt-0.5">
                {rec.reason || 'Automated policy engine evaluation based on multi-vector signals.'}
              </p>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">11. Policy Version</span>
              <span className="font-mono font-bold text-slate-300">{rec.policy_version || 'v15.0-phase15'}</span>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">12. Actor ID</span>
              <span className="font-mono font-bold text-slate-300">{rec.actor_id || 'SENTINEL_AUTOMATION_SERVICE'}</span>
            </div>

            <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 col-span-2">
              <span className="text-[10px] font-mono text-slate-400 block uppercase">13-16. Timestamp & Audit Reference</span>
              <div className="flex items-center justify-between font-mono text-[11px] text-slate-300 mt-1">
                <span>Time: {rec.timestamp || rec.executed_at || 'NOW'}</span>
                <span className="text-sky-400">PostgreSQL Immutable Audit Record Logged</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AutomationAuditDrawer;
