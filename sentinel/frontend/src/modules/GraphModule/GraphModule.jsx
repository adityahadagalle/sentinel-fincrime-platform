import React, { useState, useRef, useMemo, useEffect } from 'react';
import GraphCanvas from './GraphCanvas';
import TransactionDetailModal from './TransactionDetailModal';
import EntityDetailModal from './EntityDetailModal';
import ClusterDetailModal from './ClusterDetailModal';
import { extractTransactionInvestigationSubgraph } from './topologySimplifier';
import { 
  Copy, Check, ShieldAlert, Sparkles, Layers, 
  Network, Clock, AlertTriangle, Play
} from 'lucide-react';
import './GraphModule.css';

const GraphModule = ({ caseData, selectedTxId = '', actions = [], onAction, connectionStatus, newTransactionEvent }) => {
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [clusterModalNode, setClusterModalNode] = useState(null);
  const [viewMode, setViewMode] = useState('investigation'); // 'investigation' | 'full'
  const [copiedCase, setCopiedCase] = useState(false);
  const [isTracing, setIsTracing] = useState(false);

  const canvasRef = useRef(null);

  const rawNodes = useMemo(() => (Array.isArray(caseData?.nodes) ? caseData.nodes : []), [caseData?.nodes]);
  const rawEdges = useMemo(() => (Array.isArray(caseData?.edges) ? caseData.edges : []), [caseData?.edges]);
  
  const caseId = caseData?.case_id || 'CASE-15323124';
  const primaryTx = caseData?.primary_tx_id || (rawEdges[0] ? (rawEdges[0].tx_id || rawEdges[0].id) : 'TX-E6B7D984');
  const riskScore = caseData?.risk_score !== undefined ? caseData.risk_score : (caseData?.risk_level || 85);
  const caseStatus = caseData?.status || 'HIGH_RISK';

  // Transaction selection state
  const [activeTxId, setActiveTxId] = useState(selectedTxId || primaryTx);

  useEffect(() => {
    if (selectedTxId) {
      setActiveTxId(selectedTxId);
    } else if (caseData?.primary_tx_id) {
      setActiveTxId(caseData.primary_tx_id);
    }
  }, [selectedTxId, caseData?.case_id, caseData?.primary_tx_id]);

  // Available transactions in this case
  const availableTxs = useMemo(() => {
    const list = [];
    const seen = new Set();
    if (Array.isArray(caseData?.transactions)) {
      caseData.transactions.forEach(t => {
        if (t?.tx_id && !seen.has(t.tx_id)) {
          seen.add(t.tx_id);
          list.push(t);
        }
      });
    }
    rawEdges.forEach(e => {
      const tid = e.tx_id || e.id;
      if (tid && !seen.has(tid)) {
        seen.add(tid);
        list.push({ tx_id: tid, amount: e.amount, sender_account: e.source || e.from, receiver_account: e.target || e.to, risk_score: e.risk_score });
      }
    });
    return list;
  }, [caseData?.transactions, rawEdges]);

  // ── Visual Graph Simplification & Contextual Subgraph Extraction ──────────
  const simplifiedData = useMemo(() => {
    return extractTransactionInvestigationSubgraph(rawNodes, rawEdges, activeTxId, caseData);
  }, [rawNodes, rawEdges, activeTxId, caseData]);

  const activeNodes = useMemo(() => {
    if (viewMode === 'full') return rawNodes;
    return simplifiedData.nodes;
  }, [viewMode, rawNodes, simplifiedData.nodes]);

  const activeEdges = useMemo(() => {
    if (viewMode === 'full') return rawEdges;
    return simplifiedData.edges;
  }, [viewMode, rawEdges, simplifiedData.edges]);

  // Suspicious Flow Calculation
  const suspiciousFlowAmount = useMemo(() => {
    const susp = activeEdges.filter(e => e.suspicious || e.is_suspicious);
    const pool = susp.length > 0 ? susp : activeEdges;
    return pool.reduce((acc, e) => acc + Number(e.amount || 0), 0);
  }, [activeEdges]);

  // Metrics
  const metrics = useMemo(() => {
    const totalNodes = activeNodes.length;
    const totalEdges = activeEdges.length;
    const maxHops = Math.max(
      ...activeNodes.map(n => Number(n.layer || 0)),
      ...activeEdges.map(e => Number(e.hop_number || 1)),
      1
    );
    return { totalNodes, totalEdges, maxHops };
  }, [activeNodes, activeEdges]);

  const handleCopyCaseId = () => {
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(caseId);
      setCopiedCase(true);
      setTimeout(() => setCopiedCase(false), 2000);
    }
  };

  const handleTracePath = () => {
    if (isTracing) return;
    setIsTracing(true);
    canvasRef.current?.tracePath(
      () => {},
      () => setIsTracing(false)
    );
  };

  if (!caseData) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center bg-[#060B14] text-slate-400 font-mono text-xs">
        LOADING INVESTIGATION GRAPH...
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full h-full overflow-hidden select-none bg-[#060B14] text-[#F8FAFC]" style={{ height: '100vh', maxHeight: '100vh' }}>
      {/* ── TOP INVESTIGATION HEADER (EXACT REFERENCE PARITY) ──────────────────── */}
      <div className="h-12 border-b border-[#131F33] bg-[#070D1A] flex items-center justify-between px-4 shrink-0 font-['JetBrains_Mono'] text-[11px] gap-4">
        <div className="flex items-center gap-3 overflow-x-auto min-w-0">
          {/* Case Identifier + Copy */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#0B1528] border border-[#1A2C4A] shrink-0">
            <span className="text-slate-400 text-[10px] font-semibold tracking-wider">CASE</span>
            <span className="text-white font-bold tracking-tight">{caseId}</span>
            <button 
              onClick={handleCopyCaseId}
              className="text-slate-400 hover:text-sky-400 transition-colors ml-0.5"
              title="Copy Case ID"
            >
              {copiedCase ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            </button>
          </div>

          {/* Risk Level Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-red-500/50 bg-red-950/30 text-red-400 font-bold text-[10px] shrink-0">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span>{riskScore} CRITICAL</span>
          </div>

          {/* Case Status Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-emerald-500/50 bg-emerald-950/30 text-emerald-400 font-bold text-[10px] shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>{caseStatus}</span>
          </div>

          {/* Active Investigating Transaction Selector */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#0B1528] border border-sky-500/40 shrink-0">
            <span className="text-slate-400 text-[10px] uppercase font-semibold">INVESTIGATING TX</span>
            {availableTxs.length > 1 ? (
              <select
                value={activeTxId || primaryTx}
                onChange={(e) => setActiveTxId(e.target.value)}
                className="bg-transparent text-sky-300 font-bold font-mono text-[11px] focus:outline-none cursor-pointer"
              >
                {availableTxs.map(t => (
                  <option key={t.tx_id} value={t.tx_id} className="bg-[#070D1A] text-slate-200">
                    {t.tx_id} {t.amount ? `(₹${Number(t.amount).toLocaleString('en-IN')})` : ''}
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-sky-300 font-bold font-mono text-[11px]">{activeTxId || primaryTx}</span>
            )}
          </div>

          {/* Suspicious Flow Amount */}
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="text-slate-500 text-[10px] uppercase tracking-wider font-semibold">SUSPICIOUS FLOW</span>
            <span className="text-amber-400 font-bold tracking-tight">
              ₹{Number(suspiciousFlowAmount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>

          {/* Topology Hops & Entities */}
          <div className="flex items-center gap-1.5 text-slate-300 shrink-0">
            <Network className="w-3.5 h-3.5 text-sky-400" />
            <span className="text-slate-300">{metrics.maxHops} Hops · {metrics.totalNodes} Entities</span>
          </div>
        </div>

        {/* Right Action Ribbon: Mode Toggle, Trace Path, SLA Window */}
        <div className="flex items-center gap-3 shrink-0">
          {/* View Mode Toggle (Investigation vs Full Network) */}
          <div className="flex items-center gap-1 bg-[#0B1528] border border-[#1A2C4A] rounded-lg p-0.5 font-['JetBrains_Mono']">
            <button
              onClick={() => setViewMode('investigation')}
              className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-all flex items-center gap-1.5 ${
                viewMode === 'investigation'
                  ? 'bg-sky-500/25 text-sky-300 border border-sky-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Contextual Investigation Subgraph (Focal Transaction & Flow)"
            >
              <Sparkles className="w-3 h-3 text-sky-400" />
              <span>Investigation ({simplifiedData.nodes.length})</span>
            </button>
            <button
              onClick={() => setViewMode('full')}
              className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-all flex items-center gap-1.5 ${
                viewMode === 'full'
                  ? 'bg-sky-500/25 text-sky-300 border border-sky-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Complete Case Network"
            >
              <Layers className="w-3 h-3 text-slate-400" />
              <span>Full Network ({rawNodes.length})</span>
            </button>
          </div>

          {/* Trace Suspicious Path Button */}
          <button
            onClick={handleTracePath}
            disabled={isTracing}
            className={`px-2.5 py-1 rounded-lg border font-mono text-[10px] font-bold uppercase transition-all flex items-center gap-1.5 ${
              isTracing
                ? 'bg-sky-500/20 text-sky-300 border-sky-500/40 animate-pulse cursor-wait'
                : 'bg-[#0E1E38] hover:bg-[#132A50] text-sky-400 hover:text-white border-sky-600/40 shadow-sm'
            }`}
            title="Sequentially trace the transaction path step-by-step"
          >
            <Play className={`w-3 h-3 ${isTracing ? 'animate-spin' : 'text-sky-400'}`} />
            <span>{isTracing ? 'TRACING...' : 'TRACE PATH'}</span>
          </button>

          {/* SLA Window */}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[#0B1528] border border-[#1A2C4A]">
            <Clock className="w-3.5 h-3.5 text-red-400" />
            <span className="text-slate-500 text-[10px] uppercase font-semibold">SLA</span>
            <span className="text-red-400 font-bold">20m</span>
          </div>
        </div>
      </div>

      {/* ── GRAPH WORKSPACE CANVAS ────────────────────────────────────────── */}
      <div className="relative w-full flex-1 overflow-hidden" style={{ minHeight: 0 }}>
        <GraphCanvas
          ref={canvasRef}
          nodes={activeNodes}
          edges={activeEdges}
          isSimplified={viewMode === 'investigation'}
          caseData={caseData}
          onNodeClick={(n) => {
            if (!n) {
              setSelectedNode(null);
              return;
            }
            if (n.is_cluster) {
              setClusterModalNode(n);
            } else {
              setSelectedNode(n);
            }
            setSelectedEdge(null);
          }}
          onEdgeClick={(e) => {
            setSelectedEdge(e);
            setSelectedNode(null);
            if (e?.tx_id) {
              setActiveTxId(e.tx_id);
            }
          }}
          onSelectionChange={() => {}}
        />

        {/* MODALS */}
        {selectedEdge && (
          <TransactionDetailModal edge={selectedEdge} onClose={() => setSelectedEdge(null)} />
        )}

        {selectedNode && (
          <EntityDetailModal node={selectedNode} onClose={() => setSelectedNode(null)} />
        )}

        {clusterModalNode && (
          <ClusterDetailModal
            clusterNode={clusterModalNode}
            onClose={() => setClusterModalNode(null)}
            onInspectIndividualNode={(n) => {
              setSelectedNode(n);
            }}
            onExpandCluster={() => {
              setViewMode('full');
            }}
          />
        )}
      </div>
    </div>
  );
};

export default GraphModule;
