import React, { useState } from 'react';
import { 
  ShieldCheck, Activity, FileText, BookOpen, ChevronDown, ChevronRight, 
  AlertTriangle, CheckCircle2, Info, ArrowRight, Code, Shield, Layers, Database
} from 'lucide-react';
import { twMerge } from 'tailwind-merge';

const formatValue = (val) => {
  if (val === null || val === undefined) return 'N/A';
  if (typeof val === 'number') {
    if (val > 1000) return `₹${val.toLocaleString('en-IN')}`;
    return val.toString();
  }
  if (typeof val === 'boolean') return val ? 'TRUE' : 'FALSE';
  if (typeof val === 'object') return JSON.stringify(val);
  return String(val);
};

const DataRow = ({ label, value }) => (
  <div className="flex justify-between items-center py-1 border-b border-[#1E293B]/40 text-[11px] font-mono">
    <span className="text-slate-500 uppercase tracking-wider">{label.replace(/_/g, ' ')}</span>
    <span className="text-slate-200 font-semibold text-right truncate max-w-[60%]">{formatValue(value)}</span>
  </div>
);

const DetailDataBlock = ({ data }) => {
  if (!data || typeof data !== 'object') return null;
  return (
    <div className="p-2.5 rounded bg-[#020617] border border-[#1E293B] space-y-1 mt-2">
      {Object.entries(data).map(([k, v]) => (
        <DataRow key={k} label={k} value={v} />
      ))}
    </div>
  );
};

export const AnalystEvidenceViewer = ({ stageKey, data, status = 'COMPLETED', title = 'AGENT REPORT' }) => {
  const [expandedItems, setExpandedItems] = useState({});
  const [showRawJson, setShowRawJson] = useState(false);

  const toggleItem = (id) => {
    setExpandedItems(prev => ({ ...prev, [id]: !prev[id] }));
  };

  if (status === 'LOADING') {
    return (
      <div className="p-6 rounded-xl border border-sky-500/20 bg-sky-500/5 text-center space-y-2 font-mono">
        <div className="w-5 h-5 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mx-auto" />
        <div className="text-xs font-bold text-sky-400">Loading evidence collection package...</div>
        <div className="text-[10px] text-slate-400">Executing deterministic evidence agent pipeline.</div>
      </div>
    );
  }

  if (status === 'PENDING' || status === 'PENDING EXECUTION') {
    return (
      <div className="p-5 rounded-xl border border-[#1E293B] bg-[#0A0F17] flex items-center gap-3 text-xs font-mono text-slate-400">
        <span className="w-2.5 h-2.5 rounded-full border border-slate-600 shrink-0" />
        <div>
          <span className="font-bold text-slate-300">○ PENDING EXECUTION</span>
          <span className="block text-[10px] text-slate-500">Awaiting investigation pipeline execution.</span>
        </div>
      </div>
    );
  }

  if (status === 'FAILED') {
    return (
      <div className="p-5 rounded-xl border border-rose-500/30 bg-rose-500/5 flex items-center gap-3 text-xs font-mono text-rose-300">
        <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
        <div>
          <span className="font-bold text-rose-400">STAGE EXECUTION FAILED</span>
          <span className="block text-[10px] text-slate-400">Backend agent pipeline reported an execution error.</span>
        </div>
      </div>
    );
  }

  if (!data || (data.evidence && data.evidence.length === 0)) {
    return (
      <div className="p-5 rounded-xl border border-[#1E293B] bg-[#0A0F17] text-center text-xs font-mono text-slate-500 italic">
        No usable investigation findings returned for this stage.
      </div>
    );
  }

  // ── 1. PHASE 1 EVIDENCE PACKAGE RENDERER ────────────────────────────────
  if (stageKey === 'EVIDENCE' || stageKey === 'evidence' || data.evidence) {
    const summary = data.summary || {};
    const items = Array.isArray(data.evidence) ? data.evidence : [];

    const totalCount = summary.total_evidence_items ?? items.length;
    const highCount = summary.high_severity_items ?? items.filter(i => i.severity === 'HIGH').length;
    const medCount = summary.medium_severity_items ?? items.filter(i => i.severity === 'MEDIUM').length;
    const lowCount = summary.low_severity_items ?? items.filter(i => i.severity === 'LOW').length;
    const infoCount = summary.info_severity_items ?? items.filter(i => i.severity === 'INFO').length;

    return (
      <div className="space-y-4 font-sans text-xs">
        {/* Status Badge & Metric Strip */}
        <div className="p-3.5 rounded-xl border border-[#1E293B] bg-[#060B15] flex flex-wrap items-center justify-between gap-3 font-mono">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="font-bold text-emerald-400">● COMPLETED</span>
            <span className="text-slate-600">·</span>
            <span className="text-slate-300">Evidence package generated · {totalCount} findings</span>
          </div>

          {/* Metric Strip */}
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700 font-bold">
              {totalCount} TOTAL
            </span>
            <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 font-bold">
              {highCount} HIGH
            </span>
            <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 font-bold">
              {medCount} MEDIUM
            </span>
            <span className="px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800 font-bold">
              {lowCount} LOW
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
              {infoCount} INFO
            </span>
          </div>
        </div>

        {/* Evidence Findings Cards */}
        <div className="space-y-2.5">
          {items.map((item) => {
            const isExp = expandedItems[item.id];
            const hasExtraData = item.data && Object.keys(item.data).length > 0;
            return (
              <div 
                key={item.id}
                className={twMerge(
                  "p-3.5 rounded-xl border transition-all bg-[#060B15]",
                  item.severity === 'HIGH' ? "border-rose-500/30" :
                  item.severity === 'MEDIUM' ? "border-amber-500/30" :
                  "border-[#1E293B]"
                )}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2 font-mono text-[10px]">
                    <span className={twMerge(
                      "px-1.5 py-0.5 rounded font-bold uppercase border",
                      item.severity === 'HIGH' ? "bg-rose-500/10 text-rose-400 border-rose-500/30" :
                      item.severity === 'MEDIUM' ? "bg-amber-500/10 text-amber-400 border-amber-500/30" :
                      "bg-sky-500/10 text-sky-400 border-sky-500/30"
                    )}>
                      ● {item.severity}
                    </span>
                    <span className="text-slate-400 font-bold">{item.id}</span>
                    <span className="text-slate-600">·</span>
                    <span className="text-slate-400 uppercase">{item.category}</span>
                  </div>

                  <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                    SOURCE: {item.source}
                  </span>
                </div>

                <p className="text-xs text-slate-200 leading-relaxed font-medium">
                  {item.finding}
                </p>

                {hasExtraData && (
                  <div className="mt-2 pt-2 border-t border-[#1E293B]/60 flex justify-between items-center">
                    <button
                      onClick={() => toggleItem(item.id)}
                      className="text-[10px] font-mono text-sky-400 hover:text-sky-300 flex items-center gap-1 transition-colors font-semibold uppercase"
                    >
                      <span>{isExp ? 'HIDE DETAILS ↑' : 'VIEW DETAILS →'}</span>
                    </button>
                  </div>
                )}

                {isExp && <DetailDataBlock data={item.data} />}
              </div>
            );
          })}
        </div>

        {/* Collapsed Technical JSON for Developers */}
        <div className="pt-2">
          <button
            onClick={() => setShowRawJson(!showRawJson)}
            className="text-[10px] font-mono text-slate-500 hover:text-slate-300 flex items-center gap-1 transition-colors"
          >
            <Code className="w-3 h-3" />
            <span>{showRawJson ? 'Hide Technical JSON' : 'Developer Debug View (Raw JSON)'}</span>
          </button>

          {showRawJson && (
            <pre className="p-3 rounded-lg bg-[#020617] border border-[#1E293B] text-[10px] font-mono text-slate-400 overflow-x-auto mt-2 leading-relaxed max-h-48 overflow-y-auto">
              {JSON.stringify(data, null, 2)}
            </pre>
          )}
        </div>
      </div>
    );
  }

  // ── 2. PHASE 2 CONTEXTUAL REPORT RENDERER ───────────────────────────────
  if (stageKey === 'CONTEXTUAL' || stageKey === 'contextual' || data.contextual_findings) {
    const findings = Array.isArray(data.contextual_findings) ? data.contextual_findings : [];
    const patterns = Array.isArray(data.patterns) ? data.patterns : [];

    return (
      <div className="space-y-4 font-sans text-xs">
        <div className="p-3.5 rounded-xl border border-purple-500/20 bg-purple-500/5 font-mono text-xs flex justify-between items-center">
          <span className="font-bold text-purple-300">● COMPLETED · CONTEXTUAL ANALYSIS</span>
          <span className="text-[10px] text-purple-400">HEURISTIC INDEX: {((data.summary?.confidence || 0.85)).toFixed(2)}</span>
        </div>

        {patterns.length > 0 && (
          <div className="space-y-2">
            <div className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest">
              MATCHED BEHAVIORAL PATTERNS ({patterns.length})
            </div>
            <div className="flex flex-wrap gap-2">
              {patterns.map((p) => (
                <div key={p.pattern_id} className="p-2.5 rounded-lg border border-purple-500/30 bg-[#060B15] font-mono text-xs">
                  <span className="font-bold text-purple-300">{p.pattern_name}</span>
                  <span className="text-[9px] text-slate-400 block mt-0.5">ID: {p.pattern_id}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2">
          {findings.map((f) => (
            <div key={f.id} className="p-3 rounded-xl border border-[#1E293B] bg-[#060B15] space-y-1">
              <div className="flex justify-between text-[10px] font-mono">
                <span className="text-purple-400 font-bold">{f.id} · {f.type}</span>
              </div>
              <p className="text-xs text-slate-200">{f.finding}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ── 3. PHASE 3 REGULATORY REPORT RENDERER ──────────────────────────────
  if (stageKey === 'REGULATORY' || stageKey === 'regulatory' || data.regulatory_indicators) {
    const indicators = Array.isArray(data.regulatory_indicators) ? data.regulatory_indicators : [];
    return (
      <div className="space-y-3 font-sans text-xs">
        <div className="p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/5 font-mono text-xs flex justify-between items-center">
          <span className="font-bold text-amber-300">● COMPLETED · REGULATORY ASSESSMENT</span>
          <span className="text-[10px] text-amber-400">INDICATORS: {indicators.length}</span>
        </div>

        <div className="space-y-2">
          {indicators.map((r) => (
            <div key={r.id} className="p-3 rounded-xl border border-[#1E293B] bg-[#060B15] space-y-1">
              <div className="flex justify-between text-[10px] font-mono">
                <span className="text-amber-400 font-bold">{r.id} · {r.indicator_code}</span>
              </div>
              <p className="text-xs text-slate-200">{r.indicator}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ── 4. PHASE 4 AUDIT EXPLANATION RENDERER ──────────────────────────────
  if (stageKey === 'AUDIT_EXPLANATION' || stageKey === 'audit' || data.executive_summary) {
    const narrative = Array.isArray(data.investigation_narrative) ? data.investigation_narrative : [];
    return (
      <div className="space-y-3 font-sans text-xs">
        <div className="p-3.5 rounded-xl border border-teal-500/20 bg-teal-500/5 font-mono text-xs">
          <span className="font-bold text-teal-300">● COMPLETED · AUDIT EXPLANATION</span>
        </div>

        {data.executive_summary && (
          <div className="p-3 rounded-xl border border-[#1E293B] bg-[#060B15] text-xs text-slate-200 leading-relaxed">
            <span className="text-[9px] font-mono font-bold text-teal-400 uppercase block mb-1">EXECUTIVE SUMMARY</span>
            {data.executive_summary}
          </div>
        )}

        {narrative.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest block">INVESTIGATION NARRATIVE STEPPER</span>
            {narrative.map((n) => (
              <div key={n.step} className="p-2.5 rounded-lg border border-[#1E293B] bg-[#060B15] font-mono text-xs space-y-1">
                <div className="text-teal-400 font-bold">STEP {n.step}: {n.stage}</div>
                <p className="text-slate-300 font-sans text-xs">{n.statement}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── 5. FALLBACK GENERIC KEY-VALUE OBJECT RENDERER ─────────────────────────
  return (
    <div className="space-y-3 font-sans text-xs">
      <div className="p-3 rounded-xl border border-[#1E293B] bg-[#060B15]">
        <DetailDataBlock data={data} />
      </div>
    </div>
  );
};

export default AnalystEvidenceViewer;
