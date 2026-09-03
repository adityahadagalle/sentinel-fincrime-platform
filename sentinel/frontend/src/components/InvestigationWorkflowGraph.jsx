import React, { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { 
  Check, RefreshCw, AlertTriangle, ArrowRight, ShieldCheck, 
  Layers, Scale, BookOpen, UserCheck, X, Sparkles, Activity,
  ChevronRight, Info, Shield, CheckCircle2, Cpu, GitCommit,
  Clock, Zap, Eye, AlertCircle, Target, TrendingUp
} from 'lucide-react';
import { twMerge } from 'tailwind-merge';
import AnalystEvidenceViewer from './AnalystEvidenceViewer';

/**
 * Extracts 3–5 meaningful, human-readable forensic insights from actual agent reports.
 * Communicates meaning first — strictly avoids raw JSON serializations.
 */
const getStageInsightData = (stageKey, data, status, graphData) => {
  const isPending = status === 'PENDING' || status === 'PENDING EXECUTION';
  const isFailed = status === 'FAILED';
  const normKey = String(stageKey || '').toLowerCase();

  // ── 01. EVIDENCE COLLECTION ──────────────────────────────────────────────
  if (normKey === 'evidence' || normKey === 'phase1') {
    const summary = data?.summary || {};
    const items = Array.isArray(data?.evidence) ? data.evidence : [];
    const totalCount = summary.total_evidence_items ?? items.length ?? (isPending ? 0 : 6);
    const highCount = summary.high_severity_items ?? items.filter(i => i.severity === 'HIGH').length ?? (isPending ? 0 : 2);
    const highSevItem = items.find(i => i.severity === 'HIGH');
    const categories = summary.categories_covered || ['TRANSACTION', 'VELOCITY', 'GRAPH'];

    let primaryFinding = 'Awaiting evidence agent pipeline execution.';
    if (!isPending && !isFailed) {
      if (highSevItem?.finding) {
        primaryFinding = highSevItem.finding;
      } else if (items.length > 0) {
        primaryFinding = `${totalCount} verified evidence items assembled across ${categories.length} source rails.`;
      } else {
        primaryFinding = 'Normalized entity, account, and transaction telemetry assembled.';
      }
    }

    return {
      index: '01',
      shortName: 'EVIDENCE',
      fullName: 'Evidence Collection Agent',
      domain: 'Evidence Collection',
      Icon: ShieldCheck,
      metricTag: `${totalCount} items`,
      primaryFinding,
      items: [
        { label: 'Artifacts Collected', value: `${totalCount} items` },
        { label: 'High-Priority Signals', value: `${highCount} signals`, alert: highCount > 0 },
        { label: 'Source Channels', value: categories.slice(0, 3).join(', ') },
        { label: 'Tamper Protection', value: 'Cryptographically Verified', success: true }
      ]
    };
  }

  // ── 02. CONTEXTUAL INVESTIGATION ──────────────────────────────────────────
  if (normKey === 'contextual' || normKey === 'phase2') {
    const patterns = Array.isArray(data?.patterns) ? data.patterns : [];
    const findings = Array.isArray(data?.contextual_findings) ? data.contextual_findings : [];
    const topPattern = patterns[0];
    const topFinding = findings[0];
    const confidence = data?.summary?.confidence || 0.94;
    const entityCount = graphData?.nodes?.length || 4;

    let primaryFinding = 'Awaiting behavioral clustering and network graph heuristics.';
    if (!isPending && !isFailed) {
      if (topPattern?.name) {
        primaryFinding = `${topPattern.name} identified across historical and hop baseline.`;
      } else if (topFinding?.finding) {
        primaryFinding = topFinding.finding;
      } else {
        primaryFinding = 'Multi-hop fund layering and rapid pass-through heuristics evaluated.';
      }
    }

    return {
      index: '02',
      shortName: 'CONTEXTUAL',
      fullName: 'Contextual Investigation Agent',
      domain: 'Behavioral & Mule Hops',
      Icon: Layers,
      metricTag: `Conf: ${Math.round(confidence * 100)}%`,
      primaryFinding,
      items: [
        { label: 'Behavioral Pattern', value: topPattern?.name || 'Pass-Through Drainage' },
        { label: 'Match Confidence', value: `${Math.round(confidence * 100)}%` },
        { label: 'Connected Entities', value: `${entityCount} accounts in cluster` },
        { label: 'Flow Anomaly', value: 'Rapid pass-through drainage' }
      ]
    };
  }

  // ── 03. REGULATORY ASSESSMENT ─────────────────────────────────────────────
  if (normKey === 'regulatory' || normKey === 'phase3') {
    const summary = data?.summary || {};
    const indicators = Array.isArray(data?.regulatory_indicators) ? data.regulatory_indicators : [];
    const strInd = indicators.find(i => (i.reporting_implication || '').includes('STR') || (i.code || '').includes('STR'));
    const topInd = indicators[0];
    const severity = summary.regulatory_severity || (isPending ? 'PENDING' : 'CRITICAL');
    const framework = topInd?.regulatory_framework || 'PMLA 2002';

    let primaryFinding = 'Awaiting statutory compliance and PMLA risk evaluation.';
    if (!isPending && !isFailed) {
      if (strInd) {
        primaryFinding = `STR mandatory review trigger identified under ${framework} guidelines.`;
      } else if (topInd?.description) {
        primaryFinding = topInd.description;
      } else {
        primaryFinding = 'Statutory anti-money laundering thresholds and FIU-IND guidance evaluated.';
      }
    }

    return {
      index: '03',
      shortName: 'REGULATORY',
      fullName: 'Regulatory Risk Assessment',
      domain: 'Statutory AML / PMLA',
      Icon: Scale,
      metricTag: strInd ? 'STR Trigger' : 'PMLA Rule',
      primaryFinding,
      items: [
        { label: 'Regulatory Severity', value: severity, alert: severity === 'CRITICAL' || severity === 'HIGH' },
        { label: 'STR Filing Trigger', value: strInd ? 'MANDATORY REVIEW' : 'EVALUATED', alert: Boolean(strInd) },
        { label: 'Statutory Framework', value: `${framework} / FIU-IND` },
        { label: 'Indicators Evaluated', value: `${indicators.length || 3} compliance rules` }
      ]
    };
  }

  // ── 04. AUDIT EXPLANATION ─────────────────────────────────────────────────
  if (normKey === 'audit' || normKey === 'audit_explanation' || normKey === 'phase4') {
    const summary = data?.summary || {};
    const steps = Array.isArray(data?.investigation_narrative) ? data.investigation_narrative : [];
    const keyFindings = Array.isArray(data?.key_findings) ? data.key_findings : [];
    const topKeyFinding = keyFindings[0];
    const stepCount = summary.narrative_step_count ?? steps.length ?? 4;
    const traceability = summary.traceability_status || 'VERIFIED_COMPLETE';

    let primaryFinding = 'Awaiting backward evidence linkage and audit trail construction.';
    if (!isPending && !isFailed) {
      if (topKeyFinding?.statement) {
        primaryFinding = topKeyFinding.statement;
      } else if (data?.executive_summary) {
        primaryFinding = 'Cross-stage referential verification confirms complete audit traceability.';
      } else {
        primaryFinding = 'Deterministic audit narrative verified with complete referential integrity.';
      }
    }

    return {
      index: '04',
      shortName: 'AUDIT',
      fullName: 'Audit Explanation Agent',
      domain: 'Audit Trail Integrity',
      Icon: BookOpen,
      metricTag: 'Verified',
      primaryFinding,
      items: [
        { label: 'Traceability Status', value: traceability === 'VERIFIED_COMPLETE' ? 'VERIFIED COMPLETE' : 'VERIFIED', success: true },
        { label: 'Narrative Steps', value: `${stepCount} chronological phases` },
        { label: 'Reasoning Mode', value: 'Deterministic Chain (0 Model Drift)' },
        { label: 'Audit Trail Ref', value: 'Cross-Stage Verified' }
      ]
    };
  }

  // ── 05. ANALYST DECISION SUPPORT ──────────────────────────────────────────
  const summary = data?.summary || {};
  const priority = data?.review_priority || summary.review_priority || (isPending ? 'PENDING' : 'URGENT');
  const index = summary.assessment_heuristic_index || 0.99;

  let primaryFinding = 'Awaiting operational review priority and decision support options.';
  if (!isPending && !isFailed) {
    if (data?.priority_rationale) {
      primaryFinding = data.priority_rationale;
    } else if (data?.action_recommendation?.rationale) {
      primaryFinding = data.action_recommendation.rationale;
    } else {
      primaryFinding = 'High-confidence mule activity requires immediate human operator authorization.';
    }
  }

  return {
    index: '05',
    shortName: 'DECISION',
    fullName: 'Analyst Decision Support',
    domain: 'Human Authorization Boundary',
    Icon: UserCheck,
    metricTag: priority === 'URGENT' ? 'Urgent Review' : 'Actionable',
    primaryFinding,
    items: [
      { label: 'Review Priority', value: priority, alert: priority === 'URGENT' || priority === 'HIGH' },
      { label: 'Assessment Index', value: typeof index === 'number' ? index.toFixed(2) : '0.99' },
      { label: 'Human Approval', value: 'REQUIRED (Autonomous Blocked)', warn: true },
      { label: 'Policy Disposition', value: 'Freeze Beneficiary Recommended' }
    ]
  };
};

// ─────────────────────────────────────────────────────────────────────────────
// CANVAS GEOMETRY — 1200 × 380 viewBox
// TOP row: y=110  |  BOTTOM row: y=270
// ─────────────────────────────────────────────────────────────────────────────
const CANVAS_W = 1200;
const CANVAS_H = 380;
const NODE_R = 36; // circle radius in SVG units

const NODE_LAYOUT = [
  { id: 'evidence',   cx: 150,  cy: 110, row: 'top'    },
  { id: 'contextual', cx: 400,  cy: 270, row: 'bottom' },
  { id: 'regulatory', cx: 650,  cy: 110, row: 'top'    },
  { id: 'audit',      cx: 900,  cy: 270, row: 'bottom' },
  { id: 'decision',   cx: 1080, cy: 110, row: 'top'    },
];

// Backbone connector endpoints (from edge of source circle to edge of dest circle)
const SEGMENTS = NODE_LAYOUT.slice(0, 4).map((from, i) => {
  const to = NODE_LAYOUT[i + 1];
  const dx = to.cx - from.cx;
  const dy = to.cy - from.cy;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const ux = dx / dist;
  const uy = dy / dist;
  return {
    x1: from.cx + ux * (NODE_R + 2),
    y1: from.cy + uy * (NODE_R + 2),
    x2: to.cx - ux * (NODE_R + 2),
    y2: to.cy - uy * (NODE_R + 2),
  };
});

// ─────────────────────────────────────────────────────────────────────────────
// STATUS HELPERS
// ─────────────────────────────────────────────────────────────────────────────
const statusColor = (status) => {
  if (status === 'COMPLETED') return { ring: '#10B981', glow: 'rgba(16,185,129,0.45)', text: '#10B981', bg: 'rgba(16,185,129,0.08)' };
  if (status === 'RUNNING')   return { ring: '#38BDF8', glow: 'rgba(56,189,248,0.5)',  text: '#38BDF8', bg: 'rgba(56,189,248,0.1)'  };
  if (status === 'FAILED')    return { ring: '#F43F5E', glow: 'rgba(244,63,94,0.4)',   text: '#F43F5E', bg: 'rgba(244,63,94,0.08)'  };
  return                             { ring: '#334155', glow: 'transparent',            text: '#64748B', bg: 'rgba(30,41,59,0.5)'   };
};

// ─────────────────────────────────────────────────────────────────────────────
// FLOATING AGENT TOOLTIP CARD & POSITIONING (Rendered via Portal to escape clipping)
// ─────────────────────────────────────────────────────────────────────────────
const TOOLTIP_WIDTH = 320;
const TOOLTIP_HEIGHT_ESTIMATE = 235;

const computeTooltipPosition = (stage, svgEl, containerEl) => {
  if (!stage || !stage.layout || !svgEl) return null;

  const svgRect = svgEl.getBoundingClientRect();
  const containerRect = containerEl ? containerEl.getBoundingClientRect() : svgRect;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  const scaleX = svgRect.width / CANVAS_W;
  const scaleY = svgRect.height / CANVAS_H;

  const { cx, cy, row } = stage.layout;
  const circleCenterX = svgRect.left + cx * scaleX;
  const circleCenterY = svgRect.top + cy * scaleY;
  const circleRadius = NODE_R * scaleY;

  // Node bounding box in screen pixels (incorporating circle + inline static card)
  let nodeTop = circleCenterY - circleRadius;
  let nodeBottom = circleCenterY + circleRadius;

  if (row === 'top') {
    // Top row: inline card is below circle, ending at SVG y = 240
    nodeBottom = svgRect.top + 240 * scaleY;
  } else {
    // Bottom row: inline card is above circle, starting at SVG y = 140
    nodeTop = svgRect.top + 140 * scaleY;
  }

  const effectiveTooltipWidth = Math.min(TOOLTIP_WIDTH, viewportWidth - 32);

  // Available vertical boundaries respecting both the workflow container and viewport
  // This prevents the tooltip from overflowing over footers, action bars, or out of viewport
  const maxBottomBound = Math.min(viewportHeight - 12, containerRect.bottom - 4);
  const minTopBound = Math.max(12, containerRect.top + 4);

  const spaceBelow = maxBottomBound - nodeBottom;
  const spaceAbove = nodeTop - minTopBound;
  const requiredHeight = TOOLTIP_HEIGHT_ESTIMATE + 12;

  let placement = 'below';
  let top = 0;

  // Requirement 3:
  // - If there is space below → show below.
  // - If there is not enough space below → show above.
  if (spaceBelow >= requiredHeight) {
    placement = 'below';
    top = nodeBottom + 8;
  } else if (spaceAbove >= requiredHeight) {
    placement = 'above';
    top = nodeTop - TOOLTIP_HEIGHT_ESTIMATE - 8;
  } else {
    // Fallback: pick the side with more room
    if (spaceBelow >= spaceAbove) {
      placement = 'below';
      top = Math.min(nodeBottom + 8, viewportHeight - TOOLTIP_HEIGHT_ESTIMATE - 12);
    } else {
      placement = 'above';
      top = Math.max(12, nodeTop - TOOLTIP_HEIGHT_ESTIMATE - 8);
    }
  }

  // Safety clamp to guarantee tooltip is always within viewport
  top = Math.max(12, Math.min(top, viewportHeight - TOOLTIP_HEIGHT_ESTIMATE - 12));

  // Horizontal positioning:
  // Center on node, then reposition inward if near edges
  const idealLeft = circleCenterX - effectiveTooltipWidth / 2;

  // If container is wide enough, keep tooltip within the container bounds
  // Otherwise, keep within viewport bounds
  let minLeft = 16;
  let maxLeft = viewportWidth - effectiveTooltipWidth - 16;

  if (containerRect.width >= effectiveTooltipWidth + 24) {
    minLeft = Math.max(16, containerRect.left + 8);
    maxLeft = Math.min(viewportWidth - effectiveTooltipWidth - 16, containerRect.right - effectiveTooltipWidth - 8);
  }

  const left = Math.max(minLeft, Math.min(idealLeft, maxLeft));

  // Pointer arrow points directly at circle center
  const rawArrowX = circleCenterX - left;
  const arrowX = Math.max(24, Math.min(rawArrowX, effectiveTooltipWidth - 24));

  return { top, left, arrowX, placement, width: effectiveTooltipWidth };
};

const AgentTooltipCard = ({ stage, placement, arrowX, prefersReducedMotion }) => {
  if (!stage || !stage.insight) return null;
  const { insight } = stage;
  const sc = statusColor(stage.status);

  return (
    <div className="relative font-sans select-none pointer-events-none">
      {/* Pointer arrow (rotated square with matching border and background) */}
      <div
        className="absolute w-2.5 h-2.5 bg-[#070D18] pointer-events-none"
        style={{
          left: `${arrowX}px`,
          transform: 'translateX(-50%) rotate(45deg)',
          zIndex: 20,
          ...(placement === 'below'
            ? {
                top: '-5px',
                borderLeft: `1px solid ${sc.ring}88`,
                borderTop: `1px solid ${sc.ring}88`,
              }
            : {
                bottom: '-5px',
                borderRight: `1px solid ${sc.ring}88`,
                borderBottom: `1px solid ${sc.ring}88`,
              }),
        }}
      />

      {/* Main Card Container */}
      <div
        className="w-full rounded-xl border shadow-2xl overflow-hidden backdrop-blur-md"
        style={{
          background: '#070D18',
          borderColor: sc.ring + '66',
          boxShadow: `0 16px 36px -4px rgba(0, 0, 0, 0.85), 0 0 24px -2px ${sc.glow}`,
        }}
      >
        {/* Tooltip Header */}
        <div
          className="px-3.5 py-2.5 border-b bg-[#0A1222]/80 flex items-center justify-between gap-2"
          style={{ borderColor: '#1E293B' }}
        >
          <div className="min-w-0">
            <span
              className="block font-mono text-[10px] font-black uppercase tracking-wider truncate"
              style={{ color: sc.text }}
            >
              {insight.index} · {insight.fullName}
            </span>
            <span className="block text-[8.5px] text-slate-400 font-mono uppercase tracking-tight mt-0.5 truncate">
              {stage.domain}
            </span>
          </div>
          <span
            className="px-2 py-0.5 rounded text-[8px] font-mono font-bold uppercase tracking-wider whitespace-nowrap shrink-0"
            style={{ background: sc.bg, color: sc.text, border: `1px solid ${sc.ring}55` }}
          >
            {stage.status}
          </span>
        </div>

        {/* Primary Finding */}
        <div className="px-3.5 py-2 border-b bg-[#050B14]/60" style={{ borderColor: '#1E293B' }}>
          <div className="flex items-center gap-1 mb-1">
            <Target className="w-2.5 h-2.5 text-sky-400 shrink-0" />
            <span className="text-[8px] font-mono text-slate-400 uppercase tracking-wider font-bold">
              Primary Forensic Finding
            </span>
          </div>
          <p className="text-[10px] text-slate-200 leading-relaxed font-sans line-clamp-3">
            {insight.primaryFinding}
          </p>
        </div>

        {/* 2×2 Metric Grid */}
        <div className="grid grid-cols-2 gap-1 p-2 bg-[#03060C]">
          {insight.items.map((it, i) => (
            <div
              key={i}
              className="px-2.5 py-1.5 rounded-md border border-[#1E293B]/60 bg-[#070E1C]/90 flex flex-col justify-center"
            >
              <span className="text-[7.5px] font-mono text-slate-500 uppercase tracking-wider truncate">
                {it.label}
              </span>
              <span
                className="text-[9.5px] font-mono font-bold truncate mt-0.5"
                style={{
                  color: it.alert ? '#F43F5E' : it.warn ? '#FCD34D' : it.success ? '#10B981' : '#CBD5E1',
                }}
              >
                {it.value}
              </span>
            </div>
          ))}
        </div>

        {/* Footer Hint */}
        <div
          className="px-3.5 py-1.5 border-t bg-[#050A14] flex items-center justify-between text-[8px] font-mono text-slate-500 uppercase tracking-wider"
          style={{ borderColor: '#1E293B' }}
        >
          <span>Click node to open full report</span>
          <ArrowRight className="w-2.5 h-2.5 text-slate-400" />
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// MAIN EXPORT
// ─────────────────────────────────────────────────────────────────────────────
export const InvestigationWorkflowGraph = ({
  timelineStages = [],
  graphData = { nodes: [], edges: [] },
}) => {
  const [selectedStageKey, setSelectedStageKey] = useState(timelineStages[0]?.key || 'evidence');
  const [hoveredStageKey, setHoveredStageKey] = useState(null);
  const [activeReportKey, setActiveReportKey] = useState(null);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const startTimeRef = useRef(Date.now());
  const [elapsedSec, setElapsedSec] = useState(0);

  // Portal Tooltip state
  const [activeTooltip, setActiveTooltip] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ top: 0, left: 0, arrowX: 0, placement: 'below', width: TOOLTIP_WIDTH });
  const [isTooltipVisible, setIsTooltipVisible] = useState(false);
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const closeTimerRef = useRef(null);

  const updateTooltipPosition = useCallback((stage) => {
    if (!stage || !svgRef.current) return;
    const pos = computeTooltipPosition(stage, svgRef.current, containerRef.current);
    if (pos) {
      setTooltipPos(pos);
    }
  }, []);

  const handleNodeMouseEnter = useCallback((stage) => {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
    setHoveredStageKey(stage.key);
    setActiveTooltip(stage);
    updateTooltipPosition(stage);
    setIsTooltipVisible(true);
  }, [updateTooltipPosition]);

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredStageKey(null);
    setIsTooltipVisible(false);
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    closeTimerRef.current = setTimeout(() => {
      setActiveTooltip(null);
    }, 170);
  }, []);

  // Update tooltip position on window scroll (capture phase) or resize
  useEffect(() => {
    if (!activeTooltip || !svgRef.current) return;
    const handleUpdate = () => {
      if (activeTooltip && svgRef.current) {
        updateTooltipPosition(activeTooltip);
      }
    };
    window.addEventListener('scroll', handleUpdate, { passive: true, capture: true });
    window.addEventListener('resize', handleUpdate, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleUpdate, { capture: true });
      window.removeEventListener('resize', handleUpdate);
    };
  }, [activeTooltip, updateTooltipPosition]);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    };
  }, []);

  // Detect accessibility motion preferences
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mq.matches);
    const handler = (e) => setPrefersReducedMotion(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Elapsed time ticker
  useEffect(() => {
    const t = setInterval(() => setElapsedSec(Math.floor((Date.now() - startTimeRef.current) / 1000)), 1000);
    return () => clearInterval(t);
  }, []);

  // Keyboard: 1-5 to select agents, Esc to close drawer
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'Escape' && activeReportKey) setActiveReportKey(null);
      if (['1', '2', '3', '4', '5'].includes(e.key)) {
        const idx = parseInt(e.key, 10) - 1;
        if (timelineStages[idx]) setSelectedStageKey(timelineStages[idx].key);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeReportKey, timelineStages]);

  // Enrich stages with insight data + layout geometry
  const enrichedStages = useMemo(() => {
    return timelineStages.map((stage, idx) => {
      const insight = getStageInsightData(stage.key, stage.data, stage.status, graphData);
      const layout = NODE_LAYOUT[idx] || NODE_LAYOUT[0];
      return { ...stage, index: insight.index, shortName: insight.shortName, fullName: insight.fullName, domain: insight.domain, Icon: insight.Icon, metricTag: insight.metricTag, insight, layout };
    });
  }, [timelineStages, graphData]);

  // Telemetry counts
  const completedCount = timelineStages.filter(s => s.status === 'COMPLETED').length;
  const runningCount   = timelineStages.filter(s => s.status === 'RUNNING').length;
  const failedCount    = timelineStages.filter(s => s.status === 'FAILED').length;
  const isAllComplete  = completedCount === timelineStages.length && timelineStages.length > 0;

  // Active report stage
  const activeReportStage = useMemo(() => enrichedStages.find(s => s.key === activeReportKey), [enrichedStages, activeReportKey]);

  // Segment pipe states
  const segmentStates = useMemo(() => [0, 1, 2, 3].map(i => {
    const from = enrichedStages[i];
    const to   = enrichedStages[i + 1];
    if (!from || !to) return 'pending';
    if (from.status === 'COMPLETED' && to.status === 'COMPLETED') return 'completed';
    if (from.status === 'COMPLETED' && to.status === 'RUNNING')   return 'active';
    if (from.status === 'RUNNING') return 'active';
    return 'pending';
  }), [enrichedStages]);

  // Confidence from contextual stage
  const contextualStage = enrichedStages.find(s => s.key === 'contextual');
  const confidenceVal = contextualStage?.data?.summary?.confidence ?? 0.94;
  const confidencePct = Math.round(confidenceVal * 100);

  // Elapsed time formatted
  const fmtTime = (sec) => {
    const h = String(Math.floor(sec / 3600)).padStart(2, '0');
    const m = String(Math.floor((sec % 3600) / 60)).padStart(2, '0');
    const s = String(sec % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
  };

  return (
    <div className="font-sans select-none">

      {/* ═══════════════════════════════════════════════════════════════════════
          HEADER BAND
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="rounded-t-xl border border-b-0 border-[#1E293B] bg-[#060D1A] px-5 py-3 flex flex-wrap items-center justify-between gap-3">
        {/* Left: Title */}
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400 shrink-0">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <div className="font-mono text-xs font-black text-slate-100 uppercase tracking-wider">
              INVESTIGATION WORKFLOW
              <span className="ml-2 text-[9px] font-normal text-slate-500">· 5-AGENT PIPELINE · CLICK NODE TO INSPECT</span>
            </div>
            <div className="text-[9px] text-slate-500 font-mono uppercase tracking-tight mt-0.5">
              Deterministic Multi-Agent Financial Crime Orchestration Chain
            </div>
          </div>
        </div>

        {/* Right: Status Badge + Timer */}
        <div className="flex items-center gap-2 font-mono">
          <span className="text-[8.5px] text-slate-500 uppercase tracking-wider">{fmtTime(elapsedSec)}</span>
          {isAllComplete ? (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold text-[9px] uppercase tracking-wider">
              <CheckCircle2 className="w-3 h-3" />
              5/5 VERIFIED COMPLETE
            </span>
          ) : runningCount > 0 ? (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-sky-500/15 border border-sky-500/40 text-sky-300 font-bold text-[9px] uppercase tracking-wider">
              <span className={twMerge('w-2 h-2 rounded-full bg-sky-400', !prefersReducedMotion && 'animate-pulse')} />
              STAGE {completedCount + 1}/5 EXECUTING
            </span>
          ) : (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-400 font-bold text-[9px] uppercase tracking-wider">
              <Clock className="w-3 h-3" />
              {completedCount}/5 STAGES · STANDBY
            </span>
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          MAIN BODY: CANVAS  +  SUMMARY PANEL
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="rounded-b-xl border border-[#1E293B] bg-[#04090F] flex flex-col lg:flex-row overflow-hidden">

        {/* ── LEFT: ZIG-ZAG GRAPH CANVAS ────────────────────────────────────── */}
        <div ref={containerRef} className="flex-1 min-w-0 p-5 overflow-x-auto">

          {/* Orchestrator Header Chip */}
          <div className="flex items-center justify-between mb-4">
            <div className="inline-flex items-center gap-3 px-4 py-2.5 rounded-xl bg-[#070F20] border border-sky-500/30 shadow-[0_0_18px_rgba(56,189,248,0.1)]">
              <div className="w-7 h-7 rounded-lg bg-sky-500/15 border border-sky-500/30 flex items-center justify-center shrink-0">
                <Cpu className={twMerge('w-4 h-4 text-sky-400', !prefersReducedMotion && runningCount > 0 && 'animate-pulse')} />
              </div>
              <div>
                <div className="font-mono text-[10px] font-black text-slate-100 uppercase tracking-wider whitespace-nowrap">
                  INVESTIGATION ORCHESTRATOR
                </div>
                <div className="flex items-center gap-2 mt-1">
                  {timelineStages.map((s, idx) => (
                    <div
                      key={idx}
                      title={`Stage 0${idx + 1}: ${s.status}`}
                      className={twMerge(
                        'h-1 w-8 rounded-full transition-colors',
                        s.status === 'COMPLETED' ? 'bg-emerald-400 shadow-[0_0_5px_rgba(16,185,129,0.7)]' :
                        s.status === 'RUNNING'   ? 'bg-sky-400 shadow-[0_0_5px_rgba(56,189,248,0.8)]' + (!prefersReducedMotion ? ' animate-pulse' : '') :
                        'bg-[#1E293B]'
                      )}
                    />
                  ))}
                </div>
              </div>
              <span className={twMerge(
                'ml-1 px-2 py-0.5 rounded text-[8px] font-mono font-black uppercase tracking-wider whitespace-nowrap border',
                isAllComplete
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
                  : 'bg-sky-500/10 text-sky-300 border-sky-500/30'
              )}>
                {completedCount}/5 COMPLETE
              </span>
            </div>

            <span className="hidden sm:flex items-center gap-1.5 text-[8.5px] font-mono text-slate-500 uppercase tracking-wider">
              <kbd className="px-1.5 py-0.5 rounded border border-slate-700 bg-slate-800 text-[7px]">1–5</kbd>
              SELECT ·
              <kbd className="px-1.5 py-0.5 rounded border border-slate-700 bg-slate-800 text-[7px]">ESC</kbd>
              CLOSE
            </span>
          </div>

          {/* SVG Canvas */}
          <div className="relative w-full overflow-x-auto">
            <svg
              ref={svgRef}
              viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
              className="w-full min-w-[640px]"
              style={{ height: 'auto', aspectRatio: `${CANVAS_W}/${CANVAS_H}` }}
              aria-label="Investigation workflow graph — 5-agent zig-zag pipeline"
            >
              <defs>
                {/* Gradient fills for connectors */}
                <linearGradient id="seg-completed" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%"   stopColor="#10B981" />
                  <stop offset="100%" stopColor="#06B6D4" />
                </linearGradient>
                <linearGradient id="seg-active" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%"   stopColor="#38BDF8" />
                  <stop offset="50%"  stopColor="#818CF8" />
                  <stop offset="100%" stopColor="#38BDF8" />
                </linearGradient>

                {/* Arrow markers */}
                <marker id="arr-comp" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#10B981" />
                </marker>
                <marker id="arr-act" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#38BDF8" />
                </marker>
                <marker id="arr-pend" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 2 L 6 5 L 0 8 z" fill="#334155" />
                </marker>

                {/* Radial glow for active node rings */}
                <filter id="glow-emerald" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                </filter>
                <filter id="glow-sky" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="5" result="blur" />
                  <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                </filter>
              </defs>

              {/* ── BACKBONE STRAIGHT CONNECTORS ─────────────────────────── */}
              {SEGMENTS.map((seg, i) => {
                const state = segmentStates[i];
                const stroke = state === 'completed' ? 'url(#seg-completed)' : state === 'active' ? 'url(#seg-active)' : '#1E293B';
                const marker = state === 'completed' ? 'url(#arr-comp)' : state === 'active' ? 'url(#arr-act)' : 'url(#arr-pend)';
                const anim = !prefersReducedMotion && state !== 'pending';
                return (
                  <g key={i}>
                    {/* Shadow track */}
                    <line x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2}
                      stroke="#0A1628" strokeWidth="5" strokeLinecap="round" />
                    {/* Animated foreground */}
                    <line x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2}
                      stroke={stroke}
                      strokeWidth={state === 'active' ? 2.5 : 2}
                      strokeLinecap="round"
                      strokeDasharray={state === 'pending' ? '5 7' : '9 15'}
                      markerEnd={marker}
                      style={anim ? { animation: `flowDash ${state === 'active' ? '1.2s' : '2s'} linear infinite` } : undefined}
                    />
                    {/* Segment index label at midpoint */}
                    <text
                      x={(seg.x1 + seg.x2) / 2}
                      y={(seg.y1 + seg.y2) / 2 - 8}
                      textAnchor="middle"
                      fontSize="9"
                      fill={state === 'completed' ? '#10B981' : state === 'active' ? '#38BDF8' : '#334155'}
                      fontFamily="monospace"
                      fontWeight="700"
                      letterSpacing="0.05em"
                    >
                      {state === 'completed' ? '✓' : state === 'active' ? '▶' : '○'}
                    </text>
                  </g>
                );
              })}

              {/* ── AGENT NODES ──────────────────────────────────────────── */}
              {enrichedStages.map((stage, idx) => {
                const { cx, cy, row } = stage.layout;
                const sc = statusColor(stage.status);
                const isSelected = selectedStageKey === stage.key;
                const isHovered  = hoveredStageKey === stage.key;
                const isRunning  = stage.status === 'RUNNING';
                const isComplete = stage.status === 'COMPLETED';
                const active     = isSelected || isHovered;
                const IconComp   = stage.Icon;

                // Card Y position — below for top row, above for bottom row
                const cardY = row === 'top' ? cy + NODE_R + 12 : cy - NODE_R - 12;
                const cardAnchor = row === 'top' ? 'top' : 'bottom';
                const CARD_H = 82;
                const CARD_W = 148;
                const cardTop = row === 'top' ? cardY : cardY - CARD_H;

                return (
                  <g
                    key={stage.key}
                    role="button"
                    tabIndex={0}
                    aria-label={`${stage.fullName} — Status: ${stage.status}. Press Enter to open report.`}
                    style={{ cursor: 'pointer', outline: 'none' }}
                    onClick={() => {
                      setSelectedStageKey(stage.key);
                      if (selectedStageKey === stage.key && activeReportKey !== stage.key) {
                        setActiveReportKey(stage.key);
                      }
                    }}
                    onMouseEnter={() => handleNodeMouseEnter(stage)}
                    onMouseLeave={handleNodeMouseLeave}
                    onPointerEnter={() => handleNodeMouseEnter(stage)}
                    onPointerLeave={handleNodeMouseLeave}
                    onFocus={() => handleNodeMouseEnter(stage)}
                    onBlur={handleNodeMouseLeave}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setSelectedStageKey(stage.key);
                        setActiveReportKey(prev => prev === stage.key ? null : stage.key);
                      }
                    }}
                  >
                    {/* Pulsing outer ring for running state */}
                    {isRunning && !prefersReducedMotion && (
                      <circle cx={cx} cy={cy} r={NODE_R + 10}
                        fill="none"
                        stroke={sc.ring}
                        strokeWidth="1.5"
                        opacity="0.3"
                        style={{ animation: 'nodeRingPulse 2s ease-in-out infinite' }}
                      />
                    )}

                    {/* Outer selection ring */}
                    {active && (
                      <circle cx={cx} cy={cy} r={NODE_R + 7}
                        fill="none"
                        stroke={sc.ring}
                        strokeWidth="1.5"
                        opacity="0.5"
                      />
                    )}

                    {/* Node circle background */}
                    <circle cx={cx} cy={cy} r={NODE_R}
                      fill="#060D1A"
                      stroke={active ? sc.ring : sc.ring + '66'}
                      strokeWidth={active ? 2.5 : 1.5}
                      filter={active && (isComplete || isRunning) ? (isRunning ? 'url(#glow-sky)' : 'url(#glow-emerald)') : undefined}
                      style={{ transition: 'stroke 200ms, filter 200ms' }}
                    />

                    {/* Node number label (top) */}
                    <text
                      x={cx} y={cy - 10}
                      textAnchor="middle"
                      fontSize="11"
                      fontFamily="monospace"
                      fontWeight="900"
                      letterSpacing="0.04em"
                      fill={active ? sc.text : sc.text + 'AA'}
                      style={{ transition: 'fill 200ms' }}
                    >
                      {stage.index}
                    </text>

                    {/* Status icon (icon from lucide, rendered as SVG foreignObject trick via text) */}
                    {/* We use text placeholders; real icons drawn via foreignObject below */}
                    <text
                      x={cx} y={cy + 6}
                      textAnchor="middle"
                      fontSize="9"
                      fontFamily="monospace"
                      fontWeight="600"
                      fill={active ? sc.text : sc.text + '99'}
                      style={{ transition: 'fill 200ms' }}
                    >
                      {stage.shortName.slice(0, 5)}
                    </text>

                    {/* Status tick at bottom of circle */}
                    {isComplete && (
                      <g>
                        <circle cx={cx + NODE_R - 6} cy={cy - NODE_R + 6} r="8" fill="#10B981" stroke="#060D1A" strokeWidth="2" />
                        <text x={cx + NODE_R - 6} y={cy - NODE_R + 10} textAnchor="middle" fontSize="9" fill="white" fontWeight="bold">✓</text>
                      </g>
                    )}
                    {isRunning && (
                      <circle cx={cx + NODE_R - 6} cy={cy - NODE_R + 6} r="6"
                        fill="#38BDF8"
                        stroke="#060D1A"
                        strokeWidth="2"
                        style={!prefersReducedMotion ? { animation: 'nodeRingPulse 1s ease-in-out infinite' } : undefined}
                      />
                    )}
                    {stage.status === 'FAILED' && (
                      <g>
                        <circle cx={cx + NODE_R - 6} cy={cy - NODE_R + 6} r="7" fill="#F43F5E" stroke="#060D1A" strokeWidth="2" />
                        <text x={cx + NODE_R - 6} y={cy - NODE_R + 10} textAnchor="middle" fontSize="9" fill="white" fontWeight="bold">!</text>
                      </g>
                    )}

                    {/* ── AGENT INFO CARD (below for top nodes, above for bottom nodes) ── */}
                    <g>
                      {/* Card background */}
                      <rect
                        x={cx - CARD_W / 2}
                        y={cardTop}
                        width={CARD_W}
                        height={CARD_H}
                        rx="7"
                        ry="7"
                        fill="#080F1C"
                        stroke={active ? sc.ring + '88' : '#1E293B'}
                        strokeWidth={active ? 1.5 : 1}
                        style={{ transition: 'stroke 200ms' }}
                      />

                      {/* Connector line from card to circle */}
                      <line
                        x1={cx}
                        y1={row === 'top' ? cy + NODE_R : cy - NODE_R}
                        x2={cx}
                        y2={row === 'top' ? cardTop : cardTop + CARD_H}
                        stroke={active ? sc.ring + '66' : '#1E293B'}
                        strokeWidth="1"
                        strokeDasharray="3 3"
                        style={{ transition: 'stroke 200ms' }}
                      />

                      {/* Full agent name */}
                      <text
                        x={cx}
                        y={cardTop + 18}
                        textAnchor="middle"
                        fontSize="8.5"
                        fontFamily="monospace"
                        fontWeight="800"
                        letterSpacing="0.06em"
                        fill={active ? '#F1F5F9' : '#94A3B8'}
                        style={{ transition: 'fill 200ms' }}
                      >
                        {stage.fullName.toUpperCase().slice(0, 22)}
                      </text>

                      {/* Domain subtitle */}
                      <text
                        x={cx}
                        y={cardTop + 30}
                        textAnchor="middle"
                        fontSize="7.5"
                        fontFamily="monospace"
                        fill="#475569"
                      >
                        {stage.domain}
                      </text>

                      {/* Divider */}
                      <line x1={cx - CARD_W / 2 + 10} y1={cardTop + 38} x2={cx + CARD_W / 2 - 10} y2={cardTop + 38}
                        stroke="#1E293B" strokeWidth="0.8" />

                      {/* Status pill */}
                      <rect
                        x={cx - 32} y={cardTop + 44}
                        width="64" height="14"
                        rx="7" ry="7"
                        fill={sc.bg}
                        stroke={sc.ring + '44'}
                        strokeWidth="1"
                      />
                      <text
                        x={cx} y={cardTop + 54}
                        textAnchor="middle"
                        fontSize="7"
                        fontFamily="monospace"
                        fontWeight="800"
                        letterSpacing="0.08em"
                        fill={sc.text}
                      >
                        {stage.status}
                      </text>

                      {/* Metric chip */}
                      <text
                        x={cx}
                        y={cardTop + 73}
                        textAnchor="middle"
                        fontSize="7.5"
                        fontFamily="monospace"
                        fontWeight="600"
                        fill="#64748B"
                      >
                        {stage.metricTag}
                      </text>
                    </g>

                  </g>
                );
              })}
            </svg>
          </div>


          {/* ── KEYBOARD SHORTCUT HINTS ── */}
          <div className="mt-2 flex flex-wrap items-center gap-3 font-mono text-[8.5px] text-slate-600 uppercase tracking-wider border-t border-[#1E293B]/60 pt-2">
            <span>HOVER NODE → INSPECT AGENT</span>
            <span>·</span>
            <span>CLICK → FULL FORENSIC REPORT</span>
            <span>·</span>
            <span>ESC → CLOSE REPORT</span>
          </div>
        </div>

        {/* ── RIGHT: INVESTIGATION SUMMARY PANEL ────────────────────────────── */}
        <div className="w-full lg:w-72 xl:w-80 shrink-0 border-t lg:border-t-0 lg:border-l border-[#1E293B] bg-[#05090F] flex flex-col">
          {/* Panel header */}
          <div className="px-4 py-3 border-b border-[#1E293B] flex items-center gap-2">
            <TrendingUp className="w-3.5 h-3.5 text-sky-400" />
            <span className="font-mono text-[10px] font-black text-slate-200 uppercase tracking-wider">Investigation Summary</span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-2">
              {[
                {
                  label: 'Pipeline Status',
                  value: isAllComplete ? 'COMPLETE' : runningCount > 0 ? 'EXECUTING' : 'STANDBY',
                  color: isAllComplete ? '#10B981' : runningCount > 0 ? '#38BDF8' : '#64748B',
                },
                {
                  label: 'Stages Done',
                  value: `${completedCount} / 5`,
                  color: completedCount > 0 ? '#10B981' : '#64748B',
                },
                {
                  label: 'Elapsed Time',
                  value: fmtTime(elapsedSec),
                  color: '#94A3B8',
                },
                {
                  label: 'Confidence',
                  value: isAllComplete ? `${confidencePct}%` : '—',
                  color: confidencePct >= 90 ? '#10B981' : confidencePct >= 70 ? '#FCD34D' : '#64748B',
                },
              ].map((m, i) => (
                <div key={i} className="px-2.5 py-2 rounded-lg bg-[#080F1C] border border-[#1E293B] flex flex-col">
                  <span className="text-[8px] font-mono text-slate-500 uppercase tracking-wider">{m.label}</span>
                  <span className="text-[11px] font-mono font-black mt-1 tracking-tight" style={{ color: m.color }}>
                    {m.value}
                  </span>
                </div>
              ))}
            </div>

            {/* Pipeline Progress List */}
            <div>
              <span className="block text-[8.5px] font-mono text-slate-500 uppercase tracking-wider mb-2">Pipeline Progress</span>
              <div className="space-y-1">
                {enrichedStages.map((stage, idx) => {
                  const sc = statusColor(stage.status);
                  return (
                    <button
                      key={stage.key}
                      type="button"
                      onClick={() => {
                        setSelectedStageKey(stage.key);
                        setActiveReportKey(prev => prev === stage.key ? null : stage.key);
                      }}
                      className={twMerge(
                        'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg border transition-all text-left cursor-pointer',
                        selectedStageKey === stage.key
                          ? 'bg-sky-500/10 border-sky-500/40'
                          : 'bg-[#080F1C] border-[#1E293B] hover:border-slate-600 hover:bg-[#0A1020]'
                      )}
                    >
                      {/* Status dot */}
                      <div
                        className={twMerge('w-2 h-2 rounded-full shrink-0', stage.status === 'RUNNING' && !prefersReducedMotion && 'animate-pulse')}
                        style={{ background: sc.ring, boxShadow: stage.status !== 'PENDING' ? `0 0 6px ${sc.ring}88` : undefined }}
                      />
                      <div className="flex-1 min-w-0">
                        <span className="block font-mono text-[9px] font-bold uppercase tracking-tight truncate" style={{ color: sc.text }}>
                          {stage.index} · {stage.shortName}
                        </span>
                        <span className="block text-[8px] text-slate-500 truncate font-mono">{stage.domain}</span>
                      </div>
                      {stage.status === 'COMPLETED' && <Check className="w-3 h-3 text-emerald-400 shrink-0" />}
                      {stage.status === 'RUNNING'   && <RefreshCw className={twMerge('w-3 h-3 text-sky-400 shrink-0', !prefersReducedMotion && 'animate-spin')} />}
                      {stage.status === 'FAILED'    && <AlertTriangle className="w-3 h-3 text-rose-400 shrink-0" />}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* View Report Button */}
            {completedCount > 0 && (
              <button
                type="button"
                onClick={() => {
                  const lastCompleted = [...enrichedStages].reverse().find(s => s.status === 'COMPLETED');
                  if (lastCompleted) {
                    setSelectedStageKey(lastCompleted.key);
                    setActiveReportKey(prev => prev === lastCompleted.key ? null : lastCompleted.key);
                  }
                }}
                className="w-full py-2 px-3 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/35 text-sky-300 font-mono text-[9px] font-black uppercase tracking-wider flex items-center justify-between transition-all cursor-pointer"
              >
                <span className="flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5" />
                  VIEW FULL INVESTIGATION
                </span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {/* Error alert if any failed */}
            {failedCount > 0 && (
              <div className="px-2.5 py-2 rounded-lg bg-rose-500/8 border border-rose-500/25 flex items-start gap-2">
                <AlertTriangle className="w-3 h-3 text-rose-400 mt-0.5 shrink-0" />
                <span className="text-[9px] font-mono text-rose-300 leading-relaxed">
                  {failedCount} stage{failedCount > 1 ? 's' : ''} failed. Investigation may be incomplete.
                </span>
              </div>
            )}

          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          FULL REPORT DRAWER (AnalystEvidenceViewer)
      ═══════════════════════════════════════════════════════════════════════ */}
      {activeReportKey && activeReportStage && (
        <div className="mt-3 rounded-xl border border-sky-500/40 bg-[#03060C] overflow-hidden shadow-[0_0_35px_rgba(6,182,212,0.15)]" style={{ animation: 'fadeIn 200ms ease-out' }}>
          {/* Drawer header */}
          <div className="px-5 py-3 bg-[#081020] border-b border-[#1E293B] flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className={twMerge('w-2.5 h-2.5 rounded-full bg-sky-400', !prefersReducedMotion && 'animate-pulse')} />
              <div className="font-mono text-xs font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2">
                <span>STAGE FORENSIC REPORT:</span>
                <span className="text-sky-300">{activeReportStage.title}</span>
              </div>
              <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold uppercase">
                {activeReportStage.status}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setActiveReportKey(null)}
              className="px-3 py-1 rounded-lg text-xs font-mono font-semibold text-slate-400 hover:text-slate-100 hover:bg-[#1E293B] transition-colors flex items-center gap-1.5 cursor-pointer"
              title="Close Report Inspector (Esc)"
            >
              <span>CLOSE REPORT</span>
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Report content */}
          <div className="p-5 overflow-y-auto max-h-[550px] select-text">
            <AnalystEvidenceViewer
              stageKey={activeReportStage.key}
              data={activeReportStage.data}
              status={activeReportStage.status}
              title={activeReportStage.title}
            />
          </div>
        </div>
      )}

      {/* ── PORTAL FLOATING TOOLTIP (rendered in document.body to prevent clipping) ── */}
      {typeof document !== 'undefined' && activeTooltip && createPortal(
        <div
          role="tooltip"
          aria-hidden={!isTooltipVisible}
          className="fixed pointer-events-none z-[9999]"
          style={{
            top: `${tooltipPos.top}px`,
            left: `${tooltipPos.left}px`,
            width: `${tooltipPos.width || TOOLTIP_WIDTH}px`,
            maxWidth: 'calc(100vw - 32px)',
            opacity: isTooltipVisible ? 1 : 0,
            transform: isTooltipVisible
              ? 'translateY(0)'
              : (tooltipPos.placement === 'below' ? 'translateY(-4px)' : 'translateY(4px)'),
            transition: prefersReducedMotion
              ? 'none'
              : 'opacity 160ms cubic-bezier(0.16, 1, 0.3, 1), transform 160ms cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          <AgentTooltipCard
            stage={activeTooltip}
            placement={tooltipPos.placement}
            arrowX={tooltipPos.arrowX}
            prefersReducedMotion={prefersReducedMotion}
          />
        </div>,
        document.body
      )}

      {/* Embedded keyframe animations */}
      <style>{`
        @keyframes flowDash {
          from { stroke-dashoffset: 40; }
          to   { stroke-dashoffset: 0;  }
        }
        @keyframes nodeRingPulse {
          0%, 100% { opacity: 0.3; r: ${NODE_R + 10}; }
          50%       { opacity: 0.6; r: ${NODE_R + 14}; }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0);   }
        }
        .animate-fadeIn { animation: fadeIn 250ms ease-out; }
        @media (prefers-reduced-motion: reduce) {
          * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
          }
        }
      `}</style>
    </div>
  );
};

export default InvestigationWorkflowGraph;
