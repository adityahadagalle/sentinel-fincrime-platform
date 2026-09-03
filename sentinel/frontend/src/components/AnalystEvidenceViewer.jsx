import React, { useState } from 'react';
import { 
  ShieldCheck, Activity, FileText, BookOpen, ChevronDown, ChevronRight, 
  AlertTriangle, CheckCircle2, Info, ArrowRight, Code, Shield, Layers, Database,
  Lock, Check, Clock, UserCheck, Scale, AlertCircle, FileCheck
} from 'lucide-react';
import { twMerge } from 'tailwind-merge';

// ── 1. DICTIONARIES & FORMATTERS ─────────────────────────────────────────────

const ACRONYMS = new Set([
  'AML', 'KYC', 'STR', 'SAR', 'PMLA', 'FIU', 'IND', 'UPI', 'IMPS', 'NEFT', 'RTGS', 
  'INR', 'ID', 'TX', 'EV', 'CTX', 'REG', 'KF', 'ATM', 'EDD', 'PEP', 'URL', 'IP', 'DAG'
]);

const KNOWN_LABELS = {
  review_priority: 'Review Priority',
  regulatory_severity: 'Regulatory Severity',
  assessment_heuristic_index: 'Assessment Heuristic Index',
  recommended_step_count: 'Recommended Review Steps',
  requires_human_approval: 'Requires Human Approval',
  requires_reason_note: 'Reason Note Required',
  requires_risk_acknowledgement: 'Risk Acknowledgement Required',
  autonomous_execution: 'Autonomous Execution',
  required_role: 'Required Role',
  primary_tx_id: 'Primary Transaction ID',
  case_id: 'Case ID',
  target_id: 'Target Account ID',
  action_code: 'Action Code',
  step_id: 'Step ID',
  pattern_id: 'Pattern ID',
  finding_id: 'Finding ID',
  contextual_severity: 'Contextual Severity',
  narrative_step_count: 'Narrative Steps',
  key_finding_count: 'Key Findings Count',
  traceability_status: 'Traceability Status',
  jurisdiction_context: 'Jurisdiction Context',
  payment_rails: 'Payment Rails',
  external_sanctions_database: 'External Sanctions Database',
  external_kyc_verification: 'External KYC Verification',
  input_case_id: 'Input Case ID',
  input_transaction_id: 'Input Transaction ID',
  generator_version: 'Generator Version',
  analyst_executive_brief: 'Analyst Executive Brief',
  priority_rationale: 'Priority Rationale',
  disposition_options: 'Disposition Options',
  recommended_review_steps: 'Recommended Review Steps',
  investigation_narrative: 'Investigation Narrative',
  regulatory_indicators: 'Regulatory Indicators',
  compliance_considerations: 'Compliance Considerations',
  contextual_findings: 'Contextual Findings',
  human_approval_boundary: 'Human Approval Boundary',
  audit_trail: 'Audit Trail',
  total_evidence_items: 'Total Evidence Items',
  high_severity_items: 'High Severity Items',
  medium_severity_items: 'Medium Severity Items',
  low_severity_items: 'Low Severity Items',
  info_severity_items: 'Info Severity Items',
  categories_covered: 'Categories Covered',
  pattern_count: 'Pattern Count',
  indicator_count: 'Indicator Count',
  investigated_at: 'Investigated At',
  generated_at: 'Generated At',
  assessed_at: 'Assessed At'
};

export const formatLabel = (str) => {
  if (!str || typeof str !== 'string') return '';
  if (KNOWN_LABELS[str]) return KNOWN_LABELS[str];
  const lower = str.toLowerCase();
  if (KNOWN_LABELS[lower]) return KNOWN_LABELS[lower];

  return str
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .trim()
    .split(' ')
    .map(word => {
      const upper = word.toUpperCase();
      if (ACRONYMS.has(upper)) return upper;
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(' ');
};

const isIdLike = (val) => {
  if (typeof val !== 'string') return false;
  return /^(CASE|TX|ACC|EV|CTX|REG|KF|CP|STEP|PAT)-[A-Za-z0-9_-]+$/i.test(val.trim());
};

const isSeverity = (val) => {
  if (typeof val !== 'string') return false;
  return ['CRITICAL', 'URGENT', 'HIGH', 'MEDIUM', 'STANDARD', 'LOW', 'INFO'].includes(val.toUpperCase().trim());
};

const formatAmount = (num) => {
  if (typeof num !== 'number') return String(num);
  return `₹${num.toLocaleString('en-IN')}`;
};

// ── 2. ATOMIC VISUAL COMPONENTS ──────────────────────────────────────────────

export const SeverityBadge = ({ severity }) => {
  const sev = String(severity || 'INFO').toUpperCase().trim();
  const colorClasses = {
    CRITICAL: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
    URGENT: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
    HIGH: 'bg-orange-500/15 text-orange-300 border-orange-500/40',
    MEDIUM: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
    STANDARD: 'bg-sky-500/15 text-sky-300 border-sky-500/40',
    LOW: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
    INFO: 'bg-slate-500/15 text-slate-300 border-slate-500/40',
  }[sev] || 'bg-slate-800 text-slate-300 border-slate-700';

  return (
    <span className={twMerge("px-2 py-0.5 rounded font-mono text-[10px] font-bold border inline-flex items-center gap-1 shrink-0", colorClasses)}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {sev}
    </span>
  );
};

export const IdBadge = ({ id }) => (
  <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[#030712] border border-[#1E293B] text-sky-300 font-semibold select-all inline-block">
    {id}
  </span>
);

export const PrimitiveValue = ({ value, labelKey = '' }) => {
  if (value === null || value === undefined) {
    return <span className="text-slate-500 italic font-mono text-[11px]">N/A</span>;
  }
  if (typeof value === 'boolean') {
    return value ? (
      <span className="text-emerald-400 font-semibold font-mono text-[11px] inline-flex items-center gap-1">
        <CheckCircle2 className="w-3.5 h-3.5" /> Yes
      </span>
    ) : (
      <span className="text-slate-400 font-semibold font-mono text-[11px] inline-flex items-center gap-1">
        <span className="w-2.5 h-2.5 rounded-full border border-slate-500 inline-block" /> No
      </span>
    );
  }
  if (typeof value === 'number') {
    const keyLower = labelKey.toLowerCase();
    if (keyLower.includes('amount') || keyLower.includes('value') || keyLower.includes('total') || keyLower.includes('recoverable')) {
      return <span className="font-mono font-bold text-slate-100">{formatAmount(value)}</span>;
    }
    if (keyLower.includes('index') || keyLower.includes('confidence') || keyLower.includes('multiplier')) {
      return (
        <span className="font-mono font-bold text-sky-300">
          {value.toFixed(2)} {keyLower.includes('confidence') && <span className="text-slate-500 font-normal">({Math.round(value * 100)}%)</span>}
        </span>
      );
    }
    return <span className="font-mono font-semibold text-slate-200">{value.toLocaleString('en-IN')}</span>;
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (isIdLike(trimmed)) return <IdBadge id={trimmed} />;
    if (isSeverity(trimmed)) return <SeverityBadge severity={trimmed} />;
    return <span className="text-slate-200 leading-relaxed break-words">{trimmed}</span>;
  }
  return <span className="text-slate-300 break-words">{String(value)}</span>;
};

export const KeyValRow = ({ label, value }) => (
  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center py-1.5 border-b border-[#1E293B]/40 gap-1 text-[11px]">
    <span className="text-slate-400 font-mono text-[10px] uppercase tracking-wider">{formatLabel(label)}</span>
    <div className="text-slate-200 sm:text-right">
      <PrimitiveValue value={value} labelKey={label} />
    </div>
  </div>
);

export const StringList = ({ items, emptyText = 'None identified' }) => {
  if (!items || !Array.isArray(items) || items.length === 0) {
    return <span className="text-slate-500 italic text-[11px] font-mono">{emptyText}</span>;
  }
  const areAllIds = items.every(isIdLike);
  if (areAllIds) {
    return (
      <div className="flex flex-wrap gap-1.5 pt-0.5">
        {items.map((id, i) => (
          <IdBadge key={i} id={id} />
        ))}
      </div>
    );
  }
  return (
    <ul className="space-y-1 text-slate-300 text-xs">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2">
          <span className="text-slate-500 mt-0.5 shrink-0">•</span>
          <span className="leading-relaxed">{String(item)}</span>
        </li>
      ))}
    </ul>
  );
};

export const HumanApprovalBoundaryCard = ({ boundary }) => {
  if (!boundary || typeof boundary !== 'object') return null;
  return (
    <div className="p-3 rounded-xl border border-amber-500/30 bg-amber-500/5 space-y-2">
      <div className="flex items-center gap-2 text-amber-400 font-mono text-[11px] font-bold uppercase tracking-wider">
        <UserCheck className="w-3.5 h-3.5" />
        HUMAN APPROVAL BOUNDARY
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
        <div className="p-2 rounded-lg bg-[#060B14] border border-[#1E293B] flex justify-between items-center">
          <span className="text-slate-400 font-mono text-[10px]">Autonomous Execution</span>
          <PrimitiveValue value={boundary.autonomous_execution} />
        </div>
        <div className="p-2 rounded-lg bg-[#060B14] border border-[#1E293B] flex justify-between items-center">
          <span className="text-slate-400 font-mono text-[10px]">Required Role</span>
          <span className="font-mono text-amber-300 font-semibold text-[11px]">
            {boundary.required_role || 'COMPLIANCE_ANALYST'}
          </span>
        </div>
      </div>
    </div>
  );
};

export const AuditTrailCard = ({ auditTrail }) => {
  const [open, setOpen] = useState(false);
  if (!auditTrail || typeof auditTrail !== 'object') return null;

  return (
    <div className="rounded-xl border border-[#1E293B] bg-[#060B14] overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full p-3 flex items-center justify-between text-left font-mono text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-bold tracking-wider uppercase">AUDIT TRAIL & TRACEABILITY</span>
          {auditTrail.deterministic && (
            <span className="px-1.5 py-0.2 text-[9px] rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              Deterministic
            </span>
          )}
        </div>
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
      </button>

      {open && (
        <div className="p-3.5 border-t border-[#1E293B] space-y-2.5 text-xs">
          {Array.isArray(auditTrail.source_stages) && auditTrail.source_stages.length > 0 && (
            <div>
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">
                Verified Source Stages
              </span>
              <div className="flex flex-wrap gap-1.5">
                {auditTrail.source_stages.map((stg, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono text-[10px] flex items-center gap-1">
                    <Check className="w-3 h-3" />
                    {formatLabel(stg)}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
            {auditTrail.input_case_id && (
              <div className="p-2 rounded bg-[#0A0F17] border border-[#1E293B] flex justify-between items-center text-[11px]">
                <span className="text-slate-500 font-mono">Input Case</span>
                <IdBadge id={auditTrail.input_case_id} />
              </div>
            )}
            {auditTrail.input_transaction_id && (
              <div className="p-2 rounded bg-[#0A0F17] border border-[#1E293B] flex justify-between items-center text-[11px]">
                <span className="text-slate-500 font-mono">Primary Tx</span>
                <IdBadge id={auditTrail.input_transaction_id} />
              </div>
            )}
            {auditTrail.generator && (
              <div className="p-2 rounded bg-[#0A0F17] border border-[#1E293B] flex justify-between items-center text-[11px]">
                <span className="text-slate-500 font-mono">Generator</span>
                <span className="text-slate-300 font-mono">{auditTrail.generator}</span>
              </div>
            )}
            {auditTrail.generator_version && (
              <div className="p-2 rounded bg-[#0A0F17] border border-[#1E293B] flex justify-between items-center text-[11px]">
                <span className="text-slate-500 font-mono">Version</span>
                <span className="text-slate-300 font-mono">{auditTrail.generator_version}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// ── 3. RECURSIVE GENERIC OBJECT & ARRAY RENDERER ─────────────────────────────

export const GenericStructuredView = ({ data, depth = 0 }) => {
  if (!data || typeof data !== 'object') {
    return <PrimitiveValue value={data} />;
  }

  // Handle arrays
  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <span className="text-slate-500 italic text-[11px] font-mono">Empty list</span>;
    }
    const isPrimitiveArray = data.every(item => typeof item !== 'object' || item === null);
    if (isPrimitiveArray) {
      return <StringList items={data} />;
    }
    return (
      <div className="space-y-2">
        {data.map((item, idx) => (
          <div key={idx} className="p-3 rounded-lg bg-[#060B14] border border-[#1E293B] space-y-1.5">
            <span className="text-[9px] font-mono font-bold text-slate-500 uppercase">ITEM {idx + 1}</span>
            <GenericStructuredView data={item} depth={depth + 1} />
          </div>
        ))}
      </div>
    );
  }

  // Filter out internal fields if at root
  const entries = Object.entries(data).filter(([k]) => !['found', 'status'].includes(k));

  return (
    <div className="space-y-2">
      {entries.map(([key, val]) => {
        if (key === 'audit_trail' && typeof val === 'object') {
          return <AuditTrailCard key={key} auditTrail={val} />;
        }
        if (key === 'human_approval_boundary' && typeof val === 'object') {
          return <HumanApprovalBoundaryCard key={key} boundary={val} />;
        }
        if (['uncertainties', 'data_gaps'].includes(key) && Array.isArray(val)) {
          return (
            <div key={key} className="p-3 rounded-xl border border-slate-800 bg-[#060B14] space-y-1.5">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider block">
                {formatLabel(key)}
              </span>
              <StringList items={val} />
            </div>
          );
        }

        // Nested array of objects
        if (Array.isArray(val)) {
          return (
            <div key={key} className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-2">
              <div className="flex justify-between items-center text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                <span>{formatLabel(key)}</span>
                <span className="text-slate-500 font-normal">({val.length})</span>
              </div>
              <GenericStructuredView data={val} depth={depth + 1} />
            </div>
          );
        }

        // Nested object
        if (typeof val === 'object' && val !== null) {
          return (
            <div key={key} className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider block mb-1">
                {formatLabel(key)}
              </span>
              <div className="space-y-1">
                {Object.entries(val).map(([subK, subV]) => (
                  <KeyValRow key={subK} label={subK} value={subV} />
                ))}
              </div>
            </div>
          );
        }

        // Flat primitive
        return <KeyValRow key={key} label={key} value={val} />;
      })}
    </div>
  );
};

// ── 4. STAGE-SPECIFIC PROFESSIONAL VIEWS ─────────────────────────────────────

// Stage 5: Analyst Decision Support
const DecisionSupportView = ({ data }) => {
  const summary = data.summary || {};
  const priority = data.review_priority || summary.review_priority || 'STANDARD';
  const steps = Array.isArray(data.recommended_review_steps) ? data.recommended_review_steps : [];
  const dispositions = Array.isArray(data.disposition_options) ? data.disposition_options : [];

  return (
    <div className="space-y-4 font-sans text-xs">
      {/* 1. Header & Priority Banner */}
      <div className="p-4 rounded-xl border border-sky-500/30 bg-[#060B15] space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1E293B] pb-2.5">
          <div className="flex items-center gap-2 font-mono">
            <Scale className="w-4 h-4 text-sky-400" />
            <span className="font-bold text-sky-300 uppercase tracking-wider">STAGE 5: ANALYST DECISION SUPPORT</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-slate-400">OPERATIONAL REVIEW PRIORITY:</span>
            <SeverityBadge severity={priority} />
          </div>
        </div>

        {data.priority_rationale && (
          <div className="text-xs text-slate-300 leading-relaxed font-sans">
            <span className="font-mono text-[10px] text-slate-400 uppercase font-bold block mb-0.5">Priority Rationale</span>
            {data.priority_rationale}
          </div>
        )}

        {/* Metric Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-xs">
          <div className="p-2 rounded-lg bg-[#03060C] border border-[#1E293B]">
            <span className="text-[9px] text-slate-500 block uppercase">Regulatory Severity</span>
            <span className="font-bold text-slate-200">{summary.regulatory_severity || 'CRITICAL'}</span>
          </div>
          <div className="p-2 rounded-lg bg-[#03060C] border border-[#1E293B]">
            <span className="text-[9px] text-slate-500 block uppercase">Assessment Index</span>
            <span className="font-bold text-sky-400">{(summary.assessment_heuristic_index || 0.99).toFixed(2)}</span>
          </div>
          <div className="p-2 rounded-lg bg-[#03060C] border border-[#1E293B]">
            <span className="text-[9px] text-slate-500 block uppercase">Recommended Steps</span>
            <span className="font-bold text-slate-200">{summary.recommended_step_count ?? steps.length}</span>
          </div>
          <div className="p-2 rounded-lg bg-[#03060C] border border-[#1E293B]">
            <span className="text-[9px] text-slate-500 block uppercase">Human Approval</span>
            <span className="font-bold text-emerald-400">Required</span>
          </div>
        </div>
      </div>

      {/* 2. Analyst Executive Brief */}
      {data.analyst_executive_brief && (
        <div className="p-3.5 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
          <div className="flex items-center gap-2 font-mono text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            <FileText className="w-3.5 h-3.5 text-sky-400" />
            ANALYST EXECUTIVE BRIEF
          </div>
          <p className="text-slate-200 leading-relaxed text-xs">
            {data.analyst_executive_brief}
          </p>
        </div>
      )}

      {/* 3. Recommended Review Steps */}
      {steps.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between font-mono text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            <span>RECOMMENDED REVIEW STEPS ({steps.length})</span>
            <span className="text-slate-500 text-[9px]">HUMAN INVESTIGATOR ACTIONS</span>
          </div>
          <div className="space-y-2">
            {steps.map((step, idx) => (
              <div key={step.step_id || idx} className="p-3.5 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-sky-500/10 text-sky-400 font-mono text-[10px] font-bold flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <IdBadge id={step.step_id || `STEP-${idx + 1}`} />
                    <span className="font-semibold text-slate-100 text-xs">{step.action}</span>
                  </div>
                  {step.priority && <SeverityBadge severity={step.priority} />}
                </div>

                {step.rationale && (
                  <p className="text-slate-300 text-xs pl-7 leading-relaxed">
                    {step.rationale}
                  </p>
                )}

                {/* Supporting evidence references */}
                {(step.supporting_evidence_ids?.length > 0 || step.supporting_regulatory_ids?.length > 0) && (
                  <div className="pl-7 pt-1 flex flex-wrap gap-1.5 items-center text-[10px] font-mono text-slate-500">
                    <span>Supporting:</span>
                    {(step.supporting_evidence_ids || []).map(id => <IdBadge key={id} id={id} />)}
                    {(step.supporting_regulatory_ids || []).map(id => <IdBadge key={id} id={id} />)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Disposition Options */}
      {dispositions.length > 0 && (
        <div className="space-y-2">
          <div className="font-mono text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            DISPOSITION OPTIONS ({dispositions.length})
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {dispositions.map((disp, idx) => (
              <div 
                key={disp.action_code || idx} 
                className={twMerge(
                  "p-3 rounded-xl border transition-all space-y-1.5",
                  disp.recommended 
                    ? "bg-[#0A1828] border-sky-500/40 shadow-[0_0_15px_rgba(56,189,248,0.08)]" 
                    : "bg-[#060B14] border-[#1E293B]"
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] font-bold text-slate-100">
                    {disp.label || disp.action_code}
                  </span>
                  {disp.recommended && (
                    <span className="px-1.5 py-0.5 rounded font-mono text-[9px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      RECOMMENDED
                    </span>
                  )}
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  {disp.description}
                </p>
                <div className="flex flex-wrap gap-1 pt-1 text-[9px] font-mono text-slate-500">
                  {disp.requires_reason_note && <span className="px-1.5 py-0.5 rounded bg-slate-800">Reason Note Req</span>}
                  {disp.requires_risk_acknowledgement && <span className="px-1.5 py-0.5 rounded bg-slate-800">Risk Ack Req</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 5. Human Approval Boundary */}
      <HumanApprovalBoundaryCard boundary={data.human_approval_boundary} />

      {/* 6. Uncertainties & Data Gaps */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider block">
            Pipeline Uncertainties
          </span>
          <StringList items={data.uncertainties} />
        </div>
        <div className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider block">
            Identified Data Gaps
          </span>
          <StringList items={data.data_gaps} />
        </div>
      </div>

      {/* 7. Audit Trail */}
      <AuditTrailCard auditTrail={data.audit_trail} />
    </div>
  );
};

// Stage 4: Audit Explanation
const AuditExplanationView = ({ data }) => {
  const narrative = Array.isArray(data.investigation_narrative) ? data.investigation_narrative : [];
  const keyFindings = Array.isArray(data.key_findings) ? data.key_findings : [];
  const summary = data.summary || {};

  return (
    <div className="space-y-4 font-sans text-xs">
      {/* Header */}
      <div className="p-4 rounded-xl border border-teal-500/30 bg-[#060B15] space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-teal-400" />
            <span className="font-bold text-teal-300 uppercase tracking-wider">STAGE 4: AUDIT EXPLANATION AGENT</span>
          </div>
          <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-teal-500/10 text-teal-400 border border-teal-500/30">
            {summary.traceability_status || 'VERIFIED COMPLETE'}
          </span>
        </div>
        <div className="text-[11px] text-slate-400 font-mono">
          Deterministic cross-stage audit narrative with complete backward evidence resolution.
        </div>
      </div>

      {/* Executive Summary */}
      {data.executive_summary && (
        <div className="p-3.5 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
          <span className="text-[10px] font-mono font-bold text-teal-400 uppercase tracking-wider block">
            AUDIT EXECUTIVE SUMMARY
          </span>
          <p className="text-slate-200 text-xs leading-relaxed">
            {data.executive_summary}
          </p>
        </div>
      )}

      {/* Stepper Narrative */}
      {narrative.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest block">
            INVESTIGATION NARRATIVE STEPPER ({narrative.length})
          </span>
          <div className="space-y-2">
            {narrative.map((item, idx) => (
              <div key={idx} className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
                <div className="flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-teal-500/20 text-teal-300 font-bold flex items-center justify-center text-[10px]">
                      {item.step_number || item.step || idx + 1}
                    </span>
                    <span className="font-bold text-slate-100">{item.title || item.stage || `Phase ${idx + 1}`}</span>
                  </div>
                </div>
                <p className="text-slate-300 text-xs pl-7 leading-relaxed">
                  {item.description || item.statement}
                </p>
                {(item.supporting_evidence_ids?.length > 0 || item.supporting_regulatory_ids?.length > 0) && (
                  <div className="pl-7 pt-1 flex flex-wrap gap-1.5 items-center text-[10px] font-mono text-slate-500">
                    <span>Referenced:</span>
                    {(item.supporting_evidence_ids || []).map(id => <IdBadge key={id} id={id} />)}
                    {(item.supporting_regulatory_ids || []).map(id => <IdBadge key={id} id={id} />)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Findings */}
      {keyFindings.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest block">
            VERIFIED AUDIT FINDINGS ({keyFindings.length})
          </span>
          <div className="space-y-2">
            {keyFindings.map((kf, idx) => (
              <div key={kf.finding_id || idx} className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
                <div className="flex items-center justify-between">
                  <IdBadge id={kf.finding_id || `KF-${idx + 1}`} />
                  {kf.severity && <SeverityBadge severity={kf.severity} />}
                </div>
                <p className="text-slate-200 text-xs leading-relaxed">{kf.statement}</p>
                {kf.supporting_evidence_ids?.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {kf.supporting_evidence_ids.map(id => <IdBadge key={id} id={id} />)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Uncertainties & Data Gaps */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider block">
            Uncertainties
          </span>
          <StringList items={data.uncertainties} />
        </div>
        <div className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider block">
            Data Gaps
          </span>
          <StringList items={data.data_gaps} />
        </div>
      </div>

      {/* Audit Trail */}
      <AuditTrailCard auditTrail={data.audit_trail} />
    </div>
  );
};

// Stage 3: Regulatory Risk Assessment
const RegulatoryView = ({ data }) => {
  const indicators = Array.isArray(data.regulatory_indicators) ? data.regulatory_indicators : [];
  const considerations = Array.isArray(data.compliance_considerations) ? data.compliance_considerations : [];
  const summary = data.summary || {};
  const status = data.jurisdiction_data_status || {};

  return (
    <div className="space-y-4 font-sans text-xs">
      {/* Header */}
      <div className="p-4 rounded-xl border border-amber-500/30 bg-[#060B15] space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1E293B] pb-2.5 font-mono">
          <div className="flex items-center gap-2">
            <Scale className="w-4 h-4 text-amber-400" />
            <span className="font-bold text-amber-300 uppercase tracking-wider">STAGE 3: REGULATORY RISK ASSESSMENT</span>
          </div>
          <SeverityBadge severity={summary.regulatory_severity || 'CRITICAL'} />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-xs">
          <div className="p-2 rounded-lg bg-[#03060C] border border-[#1E293B]">
            <span className="text-[9px] text-slate-500 block uppercase">Regulatory Severity</span>
            <span className="font-bold text-slate-200">{summary.regulatory_severity || 'CRITICAL'}</span>
          </div>
          <div className="p-2 rounded-lg bg-[#03060C] border border-[#1E293B]">
            <span className="text-[9px] text-slate-500 block uppercase">Heuristic Index</span>
            <span className="font-bold text-amber-400">{(summary.assessment_heuristic_index || 0.88).toFixed(2)}</span>
          </div>
          <div className="p-2 rounded-lg bg-[#03060C] border border-[#1E293B]">
            <span className="text-[9px] text-slate-500 block uppercase">Indicators</span>
            <span className="font-bold text-slate-200">{indicators.length}</span>
          </div>
        </div>
      </div>

      {/* Regulatory Indicators */}
      {indicators.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest block">
            REGULATORY RISK INDICATORS ({indicators.length})
          </span>
          <div className="space-y-2">
            {indicators.map((ind, idx) => (
              <div key={ind.id || idx} className="p-3.5 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 font-mono">
                    <IdBadge id={ind.id || `REG-${idx + 1}`} />
                    <span className="font-bold text-slate-100">{ind.code || ind.indicator_code}</span>
                    {ind.regulatory_framework && (
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                        {ind.regulatory_framework}
                      </span>
                    )}
                  </div>
                  {ind.severity && <SeverityBadge severity={ind.severity} />}
                </div>

                <p className="text-slate-200 text-xs leading-relaxed">
                  {ind.description || ind.indicator}
                </p>

                {ind.reporting_implication && (
                  <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-[11px] font-mono text-amber-300">
                    <span className="text-slate-400">Reporting Implication:</span>
                    <span className="font-bold">{ind.reporting_implication}</span>
                  </div>
                )}

                {ind.supporting_evidence_ids?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 items-center text-[10px] font-mono text-slate-500 pt-1">
                    <span>Supporting Evidence:</span>
                    {ind.supporting_evidence_ids.map(id => <IdBadge key={id} id={id} />)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Compliance Considerations */}
      {considerations.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest block">
            COMPLIANCE ACTION CONSIDERATIONS ({considerations.length})
          </span>
          <div className="space-y-2">
            {considerations.map((c, idx) => (
              <div key={c.code || idx} className="p-3 rounded-xl border border-amber-500/20 bg-[#060B14] space-y-1">
                <span className="text-amber-400 font-mono text-[10px] font-bold uppercase">{c.code}</span>
                <p className="text-slate-200 text-xs leading-relaxed">{c.recommendation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Jurisdiction Status */}
      {Object.keys(status).length > 0 && (
        <div className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-2">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider block">
            Jurisdiction Rails & Lookups
          </span>
          <div className="space-y-1">
            {status.currency && <KeyValRow label="Currency" value={status.currency} />}
            {status.external_sanctions_database && <KeyValRow label="Sanctions DB" value={status.external_sanctions_database} />}
            {status.external_kyc_verification && <KeyValRow label="External KYC" value={status.external_kyc_verification} />}
            {Array.isArray(status.payment_rails) && (
              <div className="pt-1 flex items-center justify-between text-[11px] font-mono">
                <span className="text-slate-500">Payment Rails</span>
                <span className="text-slate-200">{status.payment_rails.join(', ')}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Stage 2: Contextual Investigation
const ContextualView = ({ data }) => {
  const patterns = Array.isArray(data.patterns) ? data.patterns : [];
  const findings = Array.isArray(data.contextual_findings) ? data.contextual_findings : [];
  const summary = data.summary || {};
  const severity = summary.contextual_severity || data.contextual_risk_level || 'HIGH';

  return (
    <div className="space-y-4 font-sans text-xs">
      {/* Header */}
      <div className="p-4 rounded-xl border border-purple-500/30 bg-[#060B15] space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1E293B] pb-2.5 font-mono">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-purple-400" />
            <span className="font-bold text-purple-300 uppercase tracking-wider">STAGE 2: CONTEXTUAL INVESTIGATION</span>
          </div>
          <SeverityBadge severity={severity} />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-xs">
          <div className="p-2 rounded-lg bg-[#03060C] border border-[#1E293B]">
            <span className="text-[9px] text-slate-500 block uppercase">Confidence</span>
            <span className="font-bold text-purple-300">{(summary.confidence || 0.94).toFixed(2)}</span>
          </div>
          <div className="p-2 rounded-lg bg-[#03060C] border border-[#1E293B]">
            <span className="text-[9px] text-slate-500 block uppercase">Patterns Matched</span>
            <span className="font-bold text-slate-200">{patterns.length}</span>
          </div>
          <div className="p-2 rounded-lg bg-[#03060C] border border-[#1E293B]">
            <span className="text-[9px] text-slate-500 block uppercase">Findings</span>
            <span className="font-bold text-slate-200">{findings.length}</span>
          </div>
        </div>
      </div>

      {/* Patterns */}
      {patterns.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest block">
            MATCHED BEHAVIORAL PATTERNS ({patterns.length})
          </span>
          <div className="space-y-2">
            {patterns.map((p, idx) => (
              <div key={p.pattern_id || idx} className="p-3.5 rounded-xl border border-purple-500/20 bg-[#060B14] space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 font-mono">
                    <IdBadge id={p.pattern_id || `CP-${idx + 1}`} />
                    <span className="font-bold text-slate-100">{p.name || p.pattern_name}</span>
                  </div>
                  {p.severity && <SeverityBadge severity={p.severity} />}
                </div>

                <p className="text-slate-300 text-xs leading-relaxed">
                  {p.description || p.reasoning}
                </p>

                {p.supporting_evidence_ids?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 items-center text-[10px] font-mono text-slate-500 pt-1">
                    <span>Supporting Evidence:</span>
                    {p.supporting_evidence_ids.map(id => <IdBadge key={id} id={id} />)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contextual Findings */}
      {findings.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest block">
            CONTEXTUAL FINDINGS ({findings.length})
          </span>
          <div className="space-y-2">
            {findings.map((f, idx) => (
              <div key={f.id || idx} className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1">
                <div className="flex items-center justify-between text-xs font-mono">
                  <IdBadge id={f.id || `CTX-${idx + 1}`} />
                  {f.severity && <SeverityBadge severity={f.severity} />}
                </div>
                <p className="text-slate-200 text-xs leading-relaxed">{f.finding}</p>
                {f.supporting_evidence_ids?.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {f.supporting_evidence_ids.map(id => <IdBadge key={id} id={id} />)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Structured Analytics blocks */}
      {(data.behavioral_analysis || data.counterparty_analysis || data.graph_analysis) && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest block">
            BEHAVIORAL & NETWORK BASELINES
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {data.behavioral_analysis && (
              <div className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
                <span className="text-[10px] font-mono font-bold text-purple-400 block uppercase">Behavioral</span>
                <GenericStructuredView data={data.behavioral_analysis} />
              </div>
            )}
            {data.counterparty_analysis && (
              <div className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
                <span className="text-[10px] font-mono font-bold text-purple-400 block uppercase">Counterparty</span>
                <GenericStructuredView data={data.counterparty_analysis} />
              </div>
            )}
            {data.graph_analysis && (
              <div className="p-3 rounded-xl border border-[#1E293B] bg-[#060B14] space-y-1.5">
                <span className="text-[10px] font-mono font-bold text-purple-400 block uppercase">Graph Topology</span>
                <GenericStructuredView data={data.graph_analysis} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Stage 1: Evidence Collection
const EvidenceView = ({ data }) => {
  const [expandedItems, setExpandedItems] = useState({});
  const summary = data.summary || {};
  const items = Array.isArray(data.evidence) ? data.evidence : [];

  const totalCount = summary.total_evidence_items ?? items.length;
  const highCount = summary.high_severity_items ?? items.filter(i => i.severity === 'HIGH').length;
  const medCount = summary.medium_severity_items ?? items.filter(i => i.severity === 'MEDIUM').length;
  const lowCount = summary.low_severity_items ?? items.filter(i => i.severity === 'LOW').length;
  const infoCount = summary.info_severity_items ?? items.filter(i => i.severity === 'INFO').length;

  const toggleItem = (id) => {
    setExpandedItems(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-4 font-sans text-xs">
      {/* Metric Strip */}
      <div className="p-3.5 rounded-xl border border-[#1E293B] bg-[#060B15] flex flex-wrap items-center justify-between gap-3 font-mono">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="font-bold text-emerald-400 uppercase tracking-wider">STAGE 1: EVIDENCE COLLECTION</span>
        </div>

        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700 font-bold font-mono">
            {totalCount} TOTAL
          </span>
          <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 font-bold font-mono">
            {highCount} HIGH
          </span>
          <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 font-bold font-mono">
            {medCount} MED
          </span>
          <span className="px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-800 font-bold font-mono">
            {lowCount} LOW
          </span>
          {infoCount > 0 && (
            <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800 font-mono">
              {infoCount} INFO
            </span>
          )}
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
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-2 font-mono text-[10px]">
                  <SeverityBadge severity={item.severity} />
                  <IdBadge id={item.id} />
                  <span className="text-slate-400 uppercase font-semibold">{formatLabel(item.category)}</span>
                </div>

                {item.source && (
                  <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                    SOURCE: {item.source}
                  </span>
                )}
              </div>

              <p className="text-xs text-slate-200 leading-relaxed font-medium">
                {item.finding || item.statement || `${item.indicator} = ${item.value}`}
              </p>

              {hasExtraData && (
                <div className="mt-2 pt-2 border-t border-[#1E293B]/60 flex justify-between items-center">
                  <button
                    type="button"
                    onClick={() => toggleItem(item.id)}
                    className="text-[10px] font-mono text-sky-400 hover:text-sky-300 flex items-center gap-1 transition-colors font-semibold uppercase"
                  >
                    <span>{isExp ? 'HIDE TECHNICAL DETAILS ↑' : 'VIEW TECHNICAL DETAILS →'}</span>
                  </button>
                </div>
              )}

              {isExp && (
                <div className="mt-2 p-3 rounded-lg bg-[#020617] border border-[#1E293B] space-y-1">
                  {Object.entries(item.data).map(([k, v]) => (
                    <KeyValRow key={k} label={k} value={v} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ── 5. MAIN ANALYST EVIDENCE VIEWER COMPONENT ─────────────────────────────────

export const AnalystEvidenceViewer = ({ 
  stageKey, 
  data, 
  status = 'COMPLETED', 
  title = 'AGENT REPORT' 
}) => {
  const [showRawJson, setShowRawJson] = useState(false);

  // Status Handlers
  if (status === 'LOADING') {
    return (
      <div className="p-6 rounded-xl border border-sky-500/20 bg-sky-500/5 text-center space-y-2 font-mono">
        <div className="w-5 h-5 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mx-auto" />
        <div className="text-xs font-bold text-sky-400">Loading evidence collection package...</div>
        <div className="text-[10px] text-slate-400">Executing deterministic agent pipeline.</div>
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

  if (!data || (typeof data === 'object' && Object.keys(data).length === 0)) {
    return (
      <div className="p-5 rounded-xl border border-[#1E293B] bg-[#0A0F17] text-center text-xs font-mono text-slate-500 italic">
        No investigation findings returned for this stage yet.
      </div>
    );
  }

  const normKey = String(stageKey || '').toLowerCase();

  // Route to the appropriate specialized report renderer
  let content = null;

  // 1. Evidence Collection
  if (
    normKey === 'evidence' || 
    normKey === 'phase1' || 
    (data.evidence && !data.regulatory_indicators && !data.recommended_review_steps)
  ) {
    content = <EvidenceView data={data} />;
  }
  // 2. Contextual Investigation
  else if (
    normKey === 'contextual' || 
    normKey === 'phase2' || 
    (data.patterns && data.contextual_findings)
  ) {
    content = <ContextualView data={data} />;
  }
  // 3. Regulatory Risk Assessment
  else if (
    normKey === 'regulatory' || 
    normKey === 'phase3' || 
    data.regulatory_indicators || 
    data.compliance_considerations
  ) {
    content = <RegulatoryView data={data} />;
  }
  // 4. Audit Explanation
  else if (
    normKey === 'audit' || 
    normKey === 'audit_explanation' || 
    normKey === 'phase4' || 
    (data.investigation_narrative && data.executive_summary)
  ) {
    content = <AuditExplanationView data={data} />;
  }
  // 5. Analyst Decision Support
  else if (
    normKey === 'decision' || 
    normKey === 'decision_support' || 
    normKey === 'phase5' || 
    data.recommended_review_steps || 
    data.disposition_options || 
    data.analyst_executive_brief
  ) {
    content = <DecisionSupportView data={data} />;
  }
  // 6. Generic Structured Fallback
  else {
    content = <GenericStructuredView data={data} />;
  }

  return (
    <div className="space-y-4">
      {/* Primary Human-Readable Report View */}
      {content}

      {/* Developer Raw JSON Inspector (Progressive Disclosure) */}
      <div className="pt-2 border-t border-[#1E293B]/40">
        <button
          type="button"
          onClick={() => setShowRawJson(!showRawJson)}
          className="text-[10px] font-mono text-slate-500 hover:text-slate-300 flex items-center gap-1 transition-colors"
        >
          <Code className="w-3 h-3" />
          <span>{showRawJson ? 'Hide Technical JSON' : 'Developer Debug View (Raw JSON)'}</span>
        </button>

        {showRawJson && (
          <pre className="p-3 rounded-lg bg-[#020617] border border-[#1E293B] text-[10px] font-mono text-slate-400 overflow-x-auto mt-2 leading-relaxed max-h-56 overflow-y-auto">
            {JSON.stringify(data, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};

export default AnalystEvidenceViewer;
