import React, { useMemo, useRef, useState, useCallback, useEffect } from 'react';
import GraphCanvas from './GraphCanvas';
import TransactionDetailModal from './TransactionDetailModal';
import EntityDetailModal from './EntityDetailModal';
import InvestigationBriefModal from './InvestigationBriefModal';
import AgentReportModal from './AgentReportModal';
import './GraphModule.css';

import { getRole } from '../../roleStore';
import { 
  ZoomIn, ZoomOut, Maximize2, RotateCcw, Crosshair, 
  Search, Layers, X, Zap, Map, GitCommit,
  AlertTriangle, Activity, TrendingUp, Shield,
  ChevronRight, Clock, Eye, Brain, Cpu, WifiOff, Timer
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// ── SENTINEL TERMINAL DESIGN SYSTEM (from Stitch) ──────────────────────────
const TOPOLOGY_LABELS = {
  FAN_IN: 'AGGREGATOR FAN-IN',
  FAN_OUT: 'FAN-OUT DISTRIBUTION',
  CIRCULAR_LOOP: 'CIRCULAR FLOW',
  STRUCTURING_PASS_THROUGH: 'STRUCTURED LAYERING',
  LINEAR_CHAIN: 'MULE CHAIN',
  DIRECT_CASHOUT: 'DIRECT CASHOUT',
  MULTI_HOP_DAG: 'MULTI-HOP DAG'
};

// ── INTELLIGENCE PANEL PATTERN SIGNALS ──────────────────────────────────────
const PatternBar = ({ label, value, color }) => (
  <div className="mb-2">
    <div className="flex justify-between items-center mb-1">
      <span className="font-['Hanken_Grotesk'] text-[10px] text-slate-400 font-medium uppercase tracking-wide">{label}</span>
      <span className="font-['JetBrains_Mono'] text-[11px] font-bold" style={{ color }}>{value}%</span>
    </div>
    <div className="h-[3px] bg-slate-800 rounded-full overflow-hidden">
      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${value}%`, background: color }} />
    </div>
  </div>
);

// ── TIMELINE EVENT ──────────────────────────────────────────────────────────
const TimelineBar = ({ edges }) => {
  if (!edges || edges.length === 0) return null;

  const sortedEdges = [...edges].sort((a, b) => (a.hop_number || 1) - (b.hop_number || 1));
  const suspicious = sortedEdges.filter(e => e.suspicious);
  const normal = sortedEdges.filter(e => !e.suspicious);

  return (
    <div className="h-14 border-t border-[#1E293B] bg-[#0A0F17] flex items-center px-4 shrink-0 relative overflow-hidden">
      <div className="text-[9px] font-['Hanken_Grotesk'] font-semibold text-slate-500 uppercase tracking-widest mr-4 shrink-0 w-16">TIMELINE</div>
      <div className="flex-1 relative h-8">
        {/* Timeline axis */}
        <div className="absolute top-4 left-0 right-0 h-[1px] bg-slate-800" />
        {/* Event markers distributed along the axis */}
        {sortedEdges.map((edge, i) => {
          const pct = ((i + 1) / (sortedEdges.length + 1)) * 100;
          const isSusp = edge.suspicious;
          return (
            <div
              key={`tl-${i}`}
              className="absolute top-1 flex flex-col items-center"
              style={{ left: `${pct}%`, transform: 'translateX(-50%)' }}
            >
              {isSusp ? (
                <div className="w-0 h-0" style={{ borderLeft: '4px solid transparent', borderRight: '4px solid transparent', borderBottom: '7px solid #EF4444' }} />
              ) : (
                <div className="w-2 h-2 rounded-full bg-[#38BDF8]" style={{ opacity: 0.6 }} />
              )}
              <div className="mt-1 text-[8px] font-['JetBrains_Mono'] text-slate-600 whitespace-nowrap">
                H{edge.hop_number || (i+1)}
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-4 ml-4 shrink-0 text-[9px] font-['Hanken_Grotesk'] text-slate-500">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-[#38BDF8] opacity-60" />
          <span>{normal.length} NORMAL</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-0 h-0" style={{ borderLeft: '3px solid transparent', borderRight: '3px solid transparent', borderBottom: '5px solid #EF4444' }} />
          <span className="text-red-400">{suspicious.length} SUSPICIOUS</span>
        </div>
      </div>
    </div>
  );
};

// ── AI STATE MACHINE CONSTANTS ────────────────────────────────────────────────
const AI_STATUS = { IDLE: 'idle', LOADING: 'loading', READY: 'ready', UNAVAILABLE: 'unavailable', TIMEOUT: 'timeout', ERROR: 'error', NO_DATA: 'no_data' };

// ── AI SECTION SUB-COMPONENTS ─────────────────────────────────────────────────
const AISectionLabel = ({ children }) => (
  <div className="text-[9px] font-['JetBrains_Mono'] font-semibold text-slate-600 uppercase tracking-widest mb-1.5">{children}</div>
);

const AIConfidencePip = ({ value }) => {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 75 ? '#34D399' : pct >= 50 ? '#FBBF24' : '#F87171';
  return (
    <span className="font-['JetBrains_Mono'] text-[10px] font-bold px-1.5 py-0.5 rounded-sm ml-1.5"
      style={{ background: `${color}18`, border: `1px solid ${color}40`, color }}>
      {pct}%
    </span>
  );
};

const AIStatusBlock = ({ status, errorDetail }) => {
  const configs = {
    [AI_STATUS.LOADING]:     { icon: <Cpu className="w-4 h-4 text-sky-400 animate-spin" />, label: 'ANALYZING INVESTIGATION...', sub: 'Qwen 3:8B processing evidence', color: '#38BDF8' },
    [AI_STATUS.UNAVAILABLE]: { icon: <WifiOff className="w-4 h-4 text-slate-500" />, label: 'LOCAL AI UNAVAILABLE', sub: 'Start Ollama and ensure qwen3:8b is available', color: '#64748B' },
    [AI_STATUS.TIMEOUT]:     { icon: <Timer className="w-4 h-4 text-amber-400" />, label: 'AI ANALYSIS TIMED OUT', sub: 'Model took too long to respond', color: '#FBBF24' },
    [AI_STATUS.ERROR]:       { icon: <AlertTriangle className="w-4 h-4 text-red-400" />, label: 'INTELLIGENCE ANALYSIS FAILED', sub: errorDetail || 'Unexpected error', color: '#EF4444' },
    [AI_STATUS.NO_DATA]:     { icon: <Shield className="w-4 h-4 text-slate-500" />, label: 'INSUFFICIENT INVESTIGATION DATA', sub: 'Case data not available for analysis', color: '#64748B' },
  };
  const cfg = configs[status];
  if (!cfg) return null;
  return (
    <div className="flex flex-col items-center justify-center py-5 gap-2 text-center">
      {cfg.icon}
      <div className="font-['JetBrains_Mono'] text-[10px] font-bold" style={{ color: cfg.color }}>{cfg.label}</div>
      <div className="text-[10px] font-['Hanken_Grotesk'] text-slate-600 leading-relaxed px-2">{cfg.sub}</div>
    </div>
  );
};



// ── COMPACT LEGEND ───────────────────────────────────────────────────────────
const CompactLegend = ({ isOpen, onToggle }) => (
  <div className="bg-[#0A0F17]/95 border border-[#1E293B] rounded text-[10px] font-['Hanken_Grotesk'] shadow-2xl" style={{ backdropFilter: 'blur(8px)' }}>
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between px-3 py-2 text-slate-400 hover:text-slate-200 transition-colors"
    >
      <span className="font-semibold uppercase tracking-wider text-[9px]">LEGEND</span>
      <ChevronRight className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-90' : ''}`} />
    </button>
    {isOpen && (
      <div className="px-3 pb-3 space-y-3 border-t border-[#1E293B]">
        <div className="pt-2">
          <div className="text-[9px] font-semibold text-slate-600 uppercase tracking-widest mb-1.5">ENTITY TYPES</div>
          {[
            { sym: '●', label: 'Victim / Source', color: '#2563EB' },
            { sym: '⬡', label: 'Mule Account', color: '#DC2626' },
            { sym: '■', label: 'Collector / Hub', color: '#D97706' },
            { sym: '◇', label: 'UPI Handle', color: '#7C3AED' },
            { sym: '○', label: 'Person / Associate', color: '#64748B' },
            { sym: '▱', label: 'Merchant', color: '#059669' },
            { sym: '⬟', label: 'Cashout / Crypto', color: '#B91C1C' }
          ].map(item => (
            <div key={item.label} className="flex items-center gap-2 py-0.5">
              <span style={{ color: item.color }} className="w-4 text-center font-bold">{item.sym}</span>
              <span className="text-slate-400">{item.label}</span>
            </div>
          ))}
        </div>
        <div className="border-t border-[#1E293B] pt-2">
          <div className="text-[9px] font-semibold text-slate-600 uppercase tracking-widest mb-1.5">FLOW TYPES</div>
          {[
            { style: { borderTop: '2px solid #EF4444', borderStyle: 'dashed' }, label: 'Suspicious Path' },
            { style: { borderTop: '2px solid #38BDF8' }, label: 'Standard Transfer' },
            { style: { borderTop: '2px solid #38BDF8', filter: 'drop-shadow(0 0 3px #38BDF8)' }, label: 'Traced Route' }
          ].map(item => (
            <div key={item.label} className="flex items-center gap-2 py-0.5">
              <div className="w-8 h-0" style={item.style} />
              <span className="text-slate-400">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
);

// ── MINIMAP ──────────────────────────────────────────────────────────────────
const Minimap = ({ nodes, edges }) => (
  <div className="w-52 h-32 bg-[#0A0F17]/95 border border-[#1E293B] rounded shadow-2xl" style={{ backdropFilter: 'blur(8px)' }}>
    <div className="flex justify-between items-center px-2.5 py-1.5 border-b border-[#1E293B]">
      <span className="flex items-center gap-1 text-[9px] font-['Hanken_Grotesk'] font-semibold text-slate-500 uppercase tracking-widest">
        <Map className="w-2.5 h-2.5 text-[#38BDF8]" /> MINIMAP
      </span>
      <span className="text-[8px] font-['JetBrains_Mono'] text-slate-600">{nodes.length}N · {edges.length}E</span>
    </div>
    <div className="w-full" style={{ height: 'calc(100% - 28px)', padding: '4px' }}>
      <svg className="w-full h-full">
        {edges.map((e, i) => {
          const hop = e.hop_number || (i % 4);
          const x1 = Math.min(hop * 40 + 15, 175);
          const y1 = (i % 3) === 0 ? 15 : (i % 3) === 1 ? 35 : 55;
          const x2 = Math.min(hop * 40 + 48, 195);
          const y2 = ((i + 1) % 3) === 0 ? 15 : ((i + 1) % 3) === 1 ? 35 : 55;
          return (
            <line key={`me-${i}`} x1={x1} y1={y1} x2={x2} y2={y2}
              stroke={e.suspicious ? '#EF4444' : '#38BDF8'}
              strokeWidth="1" opacity="0.6"
              strokeDasharray={e.suspicious ? '3,2' : undefined} />
          );
        })}
        {nodes.map((n, i) => {
          const layer = n.layer || (i % 4);
          const cx = Math.min(layer * 40 + 15, 195);
          const cy = (i % 3) === 0 ? 15 : (i % 3) === 1 ? 35 : 55;
          const fill = n.node_type === 'victim' ? '#2563EB'
            : n.node_type === 'mule' ? '#DC2626'
            : n.node_type === 'collector' ? '#D97706'
            : n.node_type === 'crypto' ? '#7C3AED'
            : '#475569';
          return <circle key={`mn-${i}`} cx={cx} cy={cy} r="4" fill={fill} />;
        })}
      </svg>
    </div>
  </div>
);

// ── MAIN GRAPH MODULE ────────────────────────────────────────────────────────
const GraphModule = ({ caseData, actions = [], onAction, connectionStatus, newTransactionEvent }) => {
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [briefModalOpen, setBriefModalOpen] = useState(false);
  const [selectedAgentReport, setSelectedAgentReport] = useState(null);
  const [processingNodes, setProcessingNodes] = useState({});

  // ── AI State (Lifted to GraphModule level) ────────────────────────────────
  const [aiStatus, setAiStatus] = useState(AI_STATUS.IDLE);
  const [aiResult, setAiResult] = useState(null); // cached for current session
  const [aiError, setAiError] = useState(null);

  const handleAnalyzeCase = useCallback(async (e) => {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
    if (aiStatus === AI_STATUS.LOADING) return;
    setAiStatus(AI_STATUS.LOADING);
    setAiError(null);
    try {
      const endpoint = import.meta.env.VITE_API_URL 
        ? `${import.meta.env.VITE_API_URL.replace(/\/$/, '')}/intelligence/analyze`
        : '/intelligence/analyze';
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: caseData?.case_id }),
        signal: AbortSignal.timeout(70000),
      });
      if (!resp.ok) {
        let errText = `HTTP ${resp.status}`;
        try {
          const errJson = await resp.json();
          if (errJson.detail) errText = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        } catch {}
        throw new Error(errText);
      }
      const data = await resp.json();
      const s = data?.status || 'error';
      setAiResult(data);
      setAiStatus(
        s === 'ready' ? AI_STATUS.READY :
        s === 'unavailable' ? AI_STATUS.UNAVAILABLE :
        s === 'timeout' ? AI_STATUS.TIMEOUT :
        s === 'no_data' ? AI_STATUS.NO_DATA : AI_STATUS.ERROR
      );
      setAiError(data?.error_detail || null);
    } catch (err) {
      setAiStatus(AI_STATUS.ERROR);
      setAiError(err?.message || String(err));
    }
  }, [caseData?.case_id, aiStatus]);

  const handleOpenBrief = useCallback((e) => {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    setBriefModalOpen(true);
    if (aiStatus === AI_STATUS.IDLE) {
      handleAnalyzeCase();
    }
  }, [aiStatus, handleAnalyzeCase]);

  const [searchQuery, setSearchQuery] = useState('');
  const [isTracing, setIsTracing] = useState(false);
  const [traceProgress, setTraceProgress] = useState(null);
  const [liveToast, setLiveToast] = useState(null);
  const [legendOpen, setLegendOpen] = useState(true);

  const canvasRef = useRef(null);
  const role = getRole();

  useEffect(() => {
    if (!newTransactionEvent) return;
    setLiveToast({
      tx_id: newTransactionEvent.tx_id,
      amount: newTransactionEvent.amount,
      risk_score: newTransactionEvent.risk_score
    });
    const t = setTimeout(() => setLiveToast(null), 4000);
    return () => clearTimeout(t);
  }, [newTransactionEvent]);

  const rawNodes = useMemo(() => Array.isArray(caseData?.nodes) ? caseData.nodes : [], [caseData?.nodes]);
  const rawEdges = useMemo(() => Array.isArray(caseData?.edges) ? caseData.edges : [], [caseData?.edges]);
  const rawTopo = caseData?.topology_type || 'MULTI_HOP_DAG';
  const humanTopology = TOPOLOGY_LABELS[rawTopo] || rawTopo.replace(/_/g, ' ');
  const caseId = caseData?.case_id || 'CASE-ATTACK-001';
  const primaryTx = caseData?.primary_tx_id || (rawEdges[0] ? (rawEdges[0].tx_id || rawEdges[0].id) : 'TX-001');

  const metrics = useMemo(() => {
    const totalNodes = rawNodes.length;
    const totalEdges = rawEdges.length;
    const maxHops = Math.max(...rawNodes.map(n => Number(n.layer || 0)), ...rawEdges.map(e => Number(e.hop_number || 1)), 1);
    const totalValue = rawEdges.reduce((acc, e) => acc + Number(e.amount || 0), 0);
    const muleCount = rawNodes.filter(n => n.node_type === 'mule' || n.account_type === 'MULE').length;
    const exitCount = rawNodes.filter(n => ['cashout','crypto','merchant'].includes(n.node_type) || n.account_type === 'DESTINATION').length;
    const suspiciousFlows = rawEdges.filter(e => e.suspicious).length;
    return { totalNodes, totalEdges, maxHops, totalValue, muleCount, exitCount, suspiciousFlows };
  }, [rawNodes, rawEdges]);

  const handleAction = useCallback(async (type, payload) => {
    if (role !== 'admin') return;
    const accountId = payload?.accountId || 'GLOBAL';
    if (processingNodes[accountId]) return;
    setProcessingNodes(p => ({ ...p, [accountId]: true }));
    if (accountId !== 'GLOBAL' && canvasRef.current?.centerOn) canvasRef.current.centerOn(accountId);
    try { await onAction?.(type.toLowerCase(), payload); } catch {}
    finally { setProcessingNodes(p => { const n = {...p}; delete n[accountId]; return n; }); }
  }, [onAction, processingNodes, role]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) return;
    const node = rawNodes.find(n => String(n.accountId || n.id).toLowerCase().includes(q.toLowerCase()));
    if (node) { canvasRef.current?.centerOn(node.accountId || node.id); setSelectedNode(node); setSelectedEdge(null); return; }
    const edge = rawEdges.find(e => String(e.tx_id || e.id).toLowerCase().includes(q.toLowerCase()));
    if (edge) { canvasRef.current?.centerOn(edge.source || edge.from); setSelectedEdge(edge); setSelectedNode(null); }
  };

  const handleTrace = () => {
    if (isTracing) { canvasRef.current?.clearHighlight(); setIsTracing(false); setTraceProgress(null); return; }
    setIsTracing(true);
    canvasRef.current?.tracePath(
      (p) => setTraceProgress(p),
      () => { setIsTracing(false); setTraceProgress(null); }
    );
  };

  if (!caseData) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center bg-[#020617] text-slate-400 font-mono text-xs">
        LOADING INVESTIGATION GRAPH...
      </div>
    );
  }

  return (
    <div
      className="flex flex-col h-full w-full overflow-hidden select-none"
      style={{ background: '#020617', color: '#F8FAFC', fontFamily: 'Hanken Grotesk, system-ui, sans-serif' }}
    >
      {/* ── SECTION 9: COMPACT INVESTIGATION HEADER ──────────────────────── */}
      <div className="h-12 border-b border-[#1E293B] flex items-center justify-between px-4 shrink-0"
        style={{ background: '#0F172A' }}>
        <div className="flex items-center gap-0 overflow-x-auto">
          {/* Case ID */}
          <div className="pr-4">
            <span className="font-['JetBrains_Mono'] text-[11px] font-bold text-[#38BDF8]">{caseId}</span>
          </div>
          <div className="w-px h-5 bg-[#1E293B] mx-0 shrink-0" />
          {/* Critical Badge */}
          <div className="px-4">
            <span className="px-2 py-0.5 text-[10px] font-['JetBrains_Mono'] font-bold rounded-sm"
              style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.45)', color: '#EF4444' }}>
              CRITICAL
            </span>
          </div>
          <div className="w-px h-5 bg-[#1E293B] shrink-0" />
          {/* Primary TX */}
          <div className="px-4 flex items-center gap-1.5">
            <span className="text-[9px] font-['Hanken_Grotesk'] text-slate-500 uppercase tracking-wider">TX</span>
            <span className="font-['JetBrains_Mono'] text-[11px] text-slate-300">{primaryTx}</span>
          </div>
          <div className="w-px h-5 bg-[#1E293B] shrink-0" />
          {/* Metrics */}
          {[
            { label: 'NODES', val: metrics.totalNodes },
            { label: 'FLOWS', val: metrics.totalEdges },
            { label: 'HOPS', val: `${metrics.maxHops}` },
            { label: 'MULES', val: metrics.muleCount },
            { label: 'EXITS', val: metrics.exitCount }
          ].map(m => (
            <React.Fragment key={m.label}>
              <div className="px-3 flex items-center gap-1.5">
                <span className="text-[9px] font-['Hanken_Grotesk'] text-slate-500 uppercase tracking-wider">{m.label}</span>
                <span className="font-['JetBrains_Mono'] text-[12px] font-bold text-slate-200">{m.val}</span>
              </div>
              <div className="w-px h-5 bg-[#1E293B] shrink-0" />
            </React.Fragment>
          ))}
          <div className="px-3 flex items-center gap-1.5">
            <span className="text-[9px] font-['Hanken_Grotesk'] text-slate-500 uppercase tracking-wider">VALUE</span>
            <span className="font-['JetBrains_Mono'] text-[12px] font-bold text-emerald-400">₹{(metrics.totalValue/100000).toFixed(1)}L</span>
          </div>
        </div>

        {/* RIGHT: Topology + live toast */}
        <div className="flex items-center gap-3 shrink-0 pl-4">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-sm border border-[#1E293B] bg-[#0B132B]">
            <Layers className="w-3 h-3 text-purple-400" />
            <span className="font-['Hanken_Grotesk'] text-[10px] font-semibold text-slate-400 uppercase tracking-wider">{humanTopology}</span>
          </div>
          {liveToast && (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-sm animate-pulse"
              style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.4)' }}>
              <Zap className="w-3 h-3 text-red-400 fill-red-400" />
              <span className="font-['JetBrains_Mono'] text-[10px] text-red-400">₹{Number(liveToast.amount||0).toLocaleString('en-IN')}</span>
            </div>
          )}
        </div>
      </div>

      {/* ── MAIN WORKSPACE ───────────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* GRAPH CANVAS AREA */}
        <div className="flex-1 relative" style={{ background: '#0B132B' }}>

          {/* Dot grid background */}
          <div className="absolute inset-0 pointer-events-none" style={{
            backgroundImage: 'radial-gradient(circle, #1E293B 1px, transparent 1px)',
            backgroundSize: '20px 20px'
          }} />

          {/* TOP-LEFT: Search + Controls */}
          <div className="absolute top-3 left-3 z-20 flex items-center gap-2">
            <form onSubmit={handleSearchSubmit} className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search entity or TX..."
                className="w-52 py-2 pl-8 pr-3 text-[11px] font-['JetBrains_Mono'] rounded outline-none placeholder-slate-600 transition-all"
                style={{
                  background: '#020617',
                  border: '1px solid #1E293B',
                  color: '#F8FAFC',
                }}
                onFocus={e => e.target.style.borderColor = '#38BDF8'}
                onBlur={e => e.target.style.borderColor = '#1E293B'}
              />
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            </form>

            <button onClick={handleTrace}
              className={`px-3 py-2 rounded text-[11px] font-['Hanken_Grotesk'] font-semibold flex items-center gap-1.5 border transition-all ${
                isTracing
                  ? 'border-red-600/60 text-red-300 animate-pulse'
                  : 'border-[#1E293B] text-slate-400 hover:border-[#38BDF8] hover:text-[#38BDF8]'
              }`}
              style={{ background: isTracing ? 'rgba(239,68,68,0.1)' : '#020617' }}
            >
              <GitCommit className="w-3.5 h-3.5" />
              {isTracing ? `HOP ${traceProgress?.step || 1}/${traceProgress?.totalSteps || '?'}` : 'TRACE PATH'}
            </button>

            <button
              onClick={handleOpenBrief}
              className="px-3.5 py-2 rounded text-[11px] font-['JetBrains_Mono'] font-bold flex items-center gap-1.5 border transition-all shadow-lg"
              style={{
                background: 'rgba(56, 189, 248, 0.12)',
                border: '1px solid rgba(56, 189, 248, 0.4)',
                color: '#38BDF8'
              }}
            >
              <Brain className="w-3.5 h-3.5 text-sky-400" />
              <span>ANALYZE BRIEF (QWEN)</span>
            </button>
          </div>

          {/* TOP-RIGHT: Zoom controls pill */}
          <div className="absolute top-3 right-3 z-20 flex flex-col gap-1 rounded border border-[#1E293B] p-1" style={{ background: '#020617' }}>
            {[
              { icon: <ZoomIn className="w-4 h-4" />, fn: () => canvasRef.current?.zoomIn(), title: 'Zoom In' },
              { icon: <ZoomOut className="w-4 h-4" />, fn: () => canvasRef.current?.zoomOut(), title: 'Zoom Out' },
              { icon: <Maximize2 className="w-4 h-4" />, fn: () => canvasRef.current?.fit(), title: 'Fit' },
              { icon: <RotateCcw className="w-3.5 h-3.5" />, fn: () => canvasRef.current?.reset(), title: 'Reset' },
              { icon: <Crosshair className="w-4 h-4" />, fn: () => canvasRef.current?.clearHighlight(), title: 'Clear' }
            ].map((ctrl, i) => (
              <button key={i} onClick={ctrl.fn} title={ctrl.title}
                className="p-2 rounded text-slate-500 hover:text-[#38BDF8] hover:bg-[#0B132B] transition-all">
                {ctrl.icon}
              </button>
            ))}
          </div>

          {/* CENTERED TRANSACTION DETAIL MODAL */}
          {selectedEdge && (
            <TransactionDetailModal edge={selectedEdge} onClose={() => setSelectedEdge(null)} />
          )}

          {/* CENTERED ENTITY DETAIL MODAL */}
          {selectedNode && (
            <EntityDetailModal node={selectedNode} onClose={() => setSelectedNode(null)} />
          )}

          {/* CYTOSCAPE CANVAS */}
          <GraphCanvas
            ref={canvasRef}
            nodes={rawNodes}
            edges={rawEdges}
            onNodeClick={n => { setSelectedNode(n); setSelectedEdge(null); }}
            onEdgeClick={e => { setSelectedEdge(e); setSelectedNode(null); }}
            onSelectionChange={() => {}}
          />

          {/* BOTTOM-LEFT: Legend */}
          <div className="absolute bottom-16 left-3 z-20">
            <CompactLegend isOpen={legendOpen} onToggle={() => setLegendOpen(o => !o)} />
          </div>

          {/* BOTTOM-RIGHT: Minimap */}
          <div className="absolute bottom-16 right-3 z-20">
            <Minimap nodes={rawNodes} edges={rawEdges} />
          </div>

          {/* CENTERED INVESTIGATION BRIEF MODAL (QWEN AI) */}
          {briefModalOpen && (
            <InvestigationBriefModal
              caseData={caseData}
              onClose={() => setBriefModalOpen(false)}
              onAnalyze={handleAnalyzeCase}
              aiStatus={aiStatus}
              aiResult={aiResult}
              aiError={aiError}
              onOpenReport={(rep) => setSelectedAgentReport(rep)}
            />
          )}

          {/* CENTERED DETAILED AGENT REPORT MODAL */}
          {selectedAgentReport && (
            <AgentReportModal
              report={selectedAgentReport}
              onClose={() => setSelectedAgentReport(null)}
            />
          )}

          {/* BOTTOM TIMELINE */}
          <div className="absolute bottom-0 left-0 right-0 z-20">
            <TimelineBar edges={rawEdges} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default GraphModule;
