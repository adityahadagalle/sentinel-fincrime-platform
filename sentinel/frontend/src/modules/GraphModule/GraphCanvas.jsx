import React, { useEffect, useRef, forwardRef, useImperativeHandle, useState, useCallback, useMemo } from 'react';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { graphStyles, isCriticalNode, getNodeClassification, NODE_CONFIG } from './graphStyles';
import { getRole } from '../../roleStore';
import { maskAccount } from '../../utils/maskAccount';
import {
  ZoomIn, ZoomOut, Maximize2, RotateCcw, Play,
  ShieldAlert, Lock, ArrowRight, UserCheck, Activity, ChevronRight, Network
} from 'lucide-react';

// Register dagre layout plugin once
try { cytoscape.use(dagre); } catch (_) { /* already registered */ }

const formatCurrency = (val) => `₹${Number(val || 0).toLocaleString('en-IN')}`;

const formatEdgeLabel = (edge) => {
  const amount = Number(edge.amount || 0);
  const channel = edge.channel || 'UPI';
  const formatted = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(amount);
  return `₹${formatted} · ${channel}`;
};

/**
 * Derives a dynamic, descriptive topology label from the actual node/edge graph structure.
 */
const deriveDynamicTopologyLabel = (nodes = [], edges = []) => {
  const nodeCount = nodes.length;
  const edgeCount = edges.length;
  if (nodeCount === 0) return 'Analyzing Telemetry (0 Nodes)';

  const inDegrees = {};
  const outDegrees = {};
  edges.forEach((e) => {
    const s = String(e.source || e.from || '');
    const t = String(e.target || e.to || '');
    outDegrees[s] = (outDegrees[s] || 0) + 1;
    inDegrees[t] = (inDegrees[t] || 0) + 1;
  });

  const maxIn = Math.max(0, ...Object.values(inDegrees));
  const maxOut = Math.max(0, ...Object.values(outDegrees));
  const hasMultipleHops = edges.some(e => Number(e.total_hops || e.hop_number || 1) > 2);

  let label = 'Linear Transfer Flow';
  if (maxIn >= 2 && maxOut <= 1) {
    label = 'Aggregator Fan-In Collection';
  } else if (maxOut >= 2 && maxIn <= 1) {
    label = 'Dispersal Fan-Out';
  } else if (edgeCount > nodeCount) {
    label = 'Circular Flow & Dispersal';
  } else if (nodeCount === 2) {
    label = 'Direct Transfer';
  } else if (hasMultipleHops || nodeCount >= 4) {
    label = 'Layered Mule Network';
  } else if (nodeCount === 3) {
    label = 'Intermediary Relay Flow';
  }

  return `${label} (${nodeCount} Nodes · ${edgeCount} Flows)`;
};



/**
 * EntityLegend — Lower-left legend matching reference screenshot.
 */
const EntityLegend = () => (
  <div className="absolute bottom-4 left-4 z-20 bg-[#060B14]/95 border border-[#1E2D4A] rounded-lg p-3 shadow-[0_8px_32px_rgba(0,0,0,0.7)] backdrop-blur-md select-none font-mono text-[9px] space-y-2 hidden md:block">
    <div className="text-[8px] text-slate-500 font-bold uppercase tracking-widest border-b border-[#1A2640] pb-1">
      Entity Geometries
    </div>
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full bg-[#2563EB] ring-1 ring-blue-400" />
        <span className="text-slate-300 font-medium">Victim Account</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-sm bg-[#DC2626] ring-1 ring-red-400" />
        <span className="text-slate-300 font-medium">Mule Account</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-sm bg-[#10B981] ring-1 ring-emerald-400" />
        <span className="text-slate-300 font-medium">Merchant Outlet</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rotate-45 bg-[#9333EA] ring-1 ring-purple-400" />
        <span className="text-slate-300 font-medium">UPI Handle</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-sm bg-[#EA580C] ring-1 ring-orange-400" />
        <span className="text-slate-300 font-medium">Cashout Terminal</span>
      </div>
    </div>
    <div className="pt-1 border-t border-[#1A2640]">
      <div className="text-[7.5px] text-slate-500 font-bold uppercase tracking-widest mb-1">Flow Paths</div>
      <div className="flex items-center gap-2">
        <span className="w-4 h-0.5 border-t border-dashed border-red-500" />
        <span className="text-red-400 font-semibold text-[8px]">Suspicious Flow</span>
      </div>
    </div>
  </div>
);

/**
 * Extract clean node telemetry using existing SENTINEL node properties
 */
const extractNodeTelemetry = (node) => {
  if (!node) return null;
  const d = typeof node.data === 'function' ? node.data() : node;
  const rawId = typeof node.id === 'function' ? node.id() : (d.id || d.accountId || '');
  return {
    id: rawId,
    accountId: rawId,
    type: d.type || d.node_type || d.account_type || 'mule',
    status: d.status || 'active',
    risk_score: d.risk_score !== undefined ? d.risk_score : (d.risk !== undefined ? d.risk : 20),
    layer: d.layer !== undefined ? d.layer : 0,
    ...d
  };
};

/**
 * SelectedEntityHUDCard — Compact card showing active/hovered entity telemetry.
 */
const SelectedEntityHUDCard = ({ nodeData }) => {
  if (!nodeData) return null;

  const id = nodeData.id || nodeData.accountId || 'ACC-COLLECTOR-HUB-3648';
  const type = (nodeData.type || nodeData.account_type || nodeData.node_type || 'MULE').toUpperCase();
  const rawRisk = nodeData.risk_score !== undefined ? nodeData.risk_score : nodeData.risk;
  const risk = rawRisk !== undefined ? Math.round(Number(rawRisk)) : 85;
  const status = String(nodeData.status || 'ACTIVE').toUpperCase();

  const badgeColor = type === 'COLLECTOR' || type === 'HUB' ? 'bg-orange-950/80 text-orange-400 border-orange-500/50'
    : type === 'DESK' || type === 'POLICE' || type === 'CRYPTO' ? 'bg-cyan-950/80 text-cyan-400 border-cyan-500/50'
    : type === 'MULE' ? 'bg-red-950/80 text-red-400 border-red-500/50'
    : type === 'MERCHANT' ? 'bg-emerald-950/80 text-emerald-400 border-emerald-500/50'
    : type === 'CASHOUT' ? 'bg-amber-950/80 text-amber-400 border-amber-500/50'
    : type === 'UPI' ? 'bg-purple-950/80 text-purple-400 border-purple-500/50'
    : 'bg-blue-950/80 text-blue-400 border-blue-500/50';

  return (
    <div className="absolute bottom-4 left-44 z-20 bg-[#060B14]/95 border border-[#1E2D4A] rounded-lg p-3 shadow-[0_8px_32px_rgba(0,0,0,0.7)] backdrop-blur-md select-none font-mono text-[10px] min-w-[210px] hidden lg:block animate-fade-in">
      <div className="flex items-center justify-between gap-2 pb-1.5 border-b border-[#1A2640]">
        <span className="text-white font-bold truncate max-w-[130px]">{id}</span>
        <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${badgeColor}`}>
          {type}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 pt-2 text-[9px]">
        <div>
          <div className="text-slate-500 uppercase text-[7.5px]">RISK SCORE</div>
          <div className="text-red-400 font-bold text-[11px] mt-0.5">{risk} / 100</div>
        </div>
        <div>
          <div className="text-slate-500 uppercase text-[7.5px]">STATUS</div>
          <div className={`font-bold text-[11px] mt-0.5 ${status === 'FLAGGED' || status === 'FROZEN' ? 'text-rose-400' : 'text-emerald-400'}`}>
            {status}
          </div>
        </div>
      </div>
    </div>
  );
};

const GraphCanvas = forwardRef(({ nodes = [], edges = [], isSimplified = true, onNodeClick, onEdgeClick, onSelectionChange, caseData = {} }, ref) => {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const onNodeClickRef = useRef(onNodeClick);
  const onEdgeClickRef = useRef(onEdgeClick);
  const onSelectionChangeRef = useRef(onSelectionChange);
  const isTracingRef = useRef(false);
  const traceTimerRef = useRef(null);
  const animFrameRef = useRef(null);

  const [hoveredNodeData, setHoveredNodeData] = useState(null);
  const [selectedNodeData, setSelectedNodeData] = useState(null);
  const hoveredNodeIdRef = useRef(null);
  const selectedNodeIdRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => { onNodeClickRef.current = onNodeClick; }, [onNodeClick]);
  useEffect(() => { onEdgeClickRef.current = onEdgeClick; }, [onEdgeClick]);
  useEffect(() => { onSelectionChangeRef.current = onSelectionChange; }, [onSelectionChange]);

  // Derive dynamic topology label from nodes & edges
  const topologyLabel = useMemo(() => {
    return deriveDynamicTopologyLabel(nodes, edges);
  }, [nodes, edges]);

  // HUD Node data binding: Hovered node takes precedence, then selected node, then default suspect/first node
  const leadNodeData = useMemo(() => {
    if (hoveredNodeData) return hoveredNodeData;
    if (selectedNodeData) return selectedNodeData;
    if (nodes.length === 0) return null;
    const suspect = nodes.find(n => {
      const t = String(n.type || n.account_type || n.node_type || '').toLowerCase();
      return t.includes('mule') || t.includes('collector') || t.includes('flagged');
    });
    return suspect || nodes[1] || nodes[0] || null;
  }, [hoveredNodeData, selectedNodeData, nodes]);

  // ── Continuous Motion Loop: Dash-Flow + Critical Node Breathing Glow ─────
  useEffect(() => {
    let offset = 0;
    const loop = () => {
      const cy = cyRef.current;
      if (cy) {
        offset = (offset + 0.5) % 24;
        cy.edges().forEach((edge) => {
          edge.style('line-dash-offset', -offset);
        });

        const time = performance.now() * 0.003;
        const pulseBlur = 18 + Math.sin(time) * 8;
        const pulseOpacity = 0.65 + Math.sin(time) * 0.25;

        cy.nodes().forEach((node) => {
          if (isCriticalNode(node) && !node.hasClass('dimmed')) {
            node.style({ 'shadow-blur': pulseBlur, 'shadow-opacity': pulseOpacity });
          }
        });
      }
      animFrameRef.current = requestAnimationFrame(loop);
    };
    animFrameRef.current = requestAnimationFrame(loop);
    return () => { if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current); };
  }, []);

  // ── Run Dagre Left-to-Right Layout ────────────────────────────────────────
  const runLayout = useCallback((cy, animate = false) => {
    if (!cy || cy.elements().length === 0) return;
    cy.layout({
      name: 'dagre',
      rankDir: 'LR',
      nodeSep: nodes.length <= 4 ? 90 : 70,
      rankSep: nodes.length <= 4 ? 200 : 160,
      edgeSep: 30,
      ranker: 'network-simplex',
      animate: false,
      padding: 90,
      fit: true
    }).run();

    // Clamp zoom so small graphs (2-3 nodes) do not over-scale into giant circles
    if (cy.zoom() > 1.05) {
      cy.zoom(0.95);
      cy.center();
    }
  }, [nodes.length]);

  // ── Controls ─────────────────────────────────────────────────────────────
  const handleZoomIn = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: cy.zoom() * 1.25, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  }, []);

  const handleZoomOut = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: cy.zoom() * 0.8, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  }, []);

  const handleFit = useCallback(() => cyRef.current?.fit(cyRef.current.elements(), 60), []);

  const handleResetLayout = useCallback(() => {
    runLayout(cyRef.current, true);
  }, [runLayout]);

  // ── Imperative Handle: Zoom, Pan, Fit, Trace ─────────────────────────────
  useImperativeHandle(ref, () => ({
    zoomIn: handleZoomIn,
    zoomOut: handleZoomOut,
    fit: handleFit,
    reset: handleResetLayout,
    centerOn: (id) => {
      const cy = cyRef.current;
      if (!cy) return;
      const ele = cy.getElementById(String(id));
      if (ele.length > 0) {
        cy.center(ele);
        cy.zoom({ level: 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
      }
    },
    clearHighlight: () => {
      const cy = cyRef.current;
      if (!cy) return;
      if (traceTimerRef.current) { clearInterval(traceTimerRef.current); traceTimerRef.current = null; }
      cy.elements().removeClass('highlighted path-highlight dimmed new-transaction-pulse traced-edge hovered-focus');
      onSelectionChangeRef.current?.(null);
    },
    tracePath: (onStepCallback, onCompleteCallback) => {
      const cy = cyRef.current;
      if (!cy || isTracingRef.current) return;
      isTracingRef.current = true;
      if (traceTimerRef.current) { clearInterval(traceTimerRef.current); traceTimerRef.current = null; }
      cy.elements().removeClass('highlighted path-highlight dimmed traced-edge');
      const sortedEdges = cy.edges().sort((a, b) => (Number(a.data('hop_number') || 1) - Number(b.data('hop_number') || 1)));
      if (sortedEdges.length === 0) {
        isTracingRef.current = false;
        return;
      }
      cy.elements().addClass('dimmed');
      let stepIndex = 0;
      traceTimerRef.current = setInterval(() => {
        if (stepIndex >= sortedEdges.length) {
          clearInterval(traceTimerRef.current);
          traceTimerRef.current = null;
          setTimeout(() => {
            cy.elements().removeClass('dimmed traced-edge');
            isTracingRef.current = false;
            onCompleteCallback?.();
          }, 1200);
          return;
        }
        const currentEdge = sortedEdges[stepIndex];
        currentEdge.removeClass('dimmed').addClass('traced-edge');
        currentEdge.source().removeClass('dimmed').addClass('highlighted');
        currentEdge.target().removeClass('dimmed').addClass('highlighted');
        onStepCallback?.({
          step: stepIndex + 1,
          totalSteps: sortedEdges.length,
          edgeId: currentEdge.id(),
          source: currentEdge.source().id(),
          target: currentEdge.target().id(),
          amount: currentEdge.data('amount'),
          hop: currentEdge.data('hop_number') || (stepIndex + 1)
        });
        stepIndex++;
      }, 450);
    }
  }));

  // ── Cytoscape Initialization ──────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: [],
      style: graphStyles,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
      minZoom: 0.15,
      maxZoom: 4.0
    });

    cyRef.current = cy;
    window.cy = cy;

    // Node click -> Select node & trigger inspector
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const neighborhood = node.neighborhood().add(node);
      cy.elements().removeClass('highlighted path-highlight dimmed traced-edge');
      cy.elements().difference(neighborhood).addClass('dimmed');
      neighborhood.addClass('highlighted');

      const nodeData = extractNodeTelemetry(node);
      selectedNodeIdRef.current = node.id();
      setSelectedNodeData(nodeData);
      hoveredNodeIdRef.current = null;
      setHoveredNodeData(null);
      onSelectionChangeRef.current?.({ type: 'node', id: node.id(), hops: neighborhood.edges().length || 1 });
      onNodeClickRef.current?.(nodeData);
    });

    // Node Hover -> Connected Edge Highlight & Graph Dim
    cy.on('mouseover', 'node', (evt) => {
      if (isTracingRef.current) return;
      const node = evt.target;
      hoveredNodeIdRef.current = node.id();
      const neighborhood = node.neighborhood().add(node);
      cy.elements().addClass('dimmed');
      neighborhood.removeClass('dimmed').addClass('hovered-focus');

      setHoveredNodeData(extractNodeTelemetry(node));
    });

    cy.on('mouseout', 'node', (evt) => {
      if (isTracingRef.current) return;
      const node = evt.target;
      if (hoveredNodeIdRef.current === node.id()) {
        hoveredNodeIdRef.current = null;
        setHoveredNodeData(null);
      }
      cy.elements().removeClass('dimmed hovered-focus');

      // If a node was previously selected, restore its focus highlighting
      if (selectedNodeIdRef.current) {
        const selEle = cy.getElementById(selectedNodeIdRef.current);
        if (selEle.length > 0) {
          const selNeighborhood = selEle.neighborhood().add(selEle);
          cy.elements().difference(selNeighborhood).addClass('dimmed');
          selNeighborhood.addClass('highlighted');
        }
      }
    });

    // Edge click -> Select transaction
    cy.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      cy.elements().removeClass('highlighted path-highlight dimmed traced-edge');
      const connected = edge.connectedNodes().add(edge);
      connected.addClass('highlighted');
      cy.elements().difference(connected).addClass('dimmed');
      onSelectionChangeRef.current?.({ type: 'edge', id: edge.id(), hops: edge.data('total_hops') || 1 });
      onEdgeClickRef.current?.(edge.data());
    });

    // Background click -> Reset focus
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        cy.elements().removeClass('highlighted path-highlight dimmed traced-edge hovered-focus');
        selectedNodeIdRef.current = null;
        setSelectedNodeData(null);
        hoveredNodeIdRef.current = null;
        setHoveredNodeData(null);
        onSelectionChangeRef.current?.(null);
        onNodeClickRef.current?.(null);
        onEdgeClickRef.current?.(null);
        setTooltip(null);
      }
    });

    // Background mouseover -> Clear temporary hover state if moving over empty canvas
    cy.on('mouseover', (evt) => {
      if (evt.target === cy) {
        if (hoveredNodeIdRef.current) {
          hoveredNodeIdRef.current = null;
          setHoveredNodeData(null);
        }
      }
    });

    return () => {
      if (traceTimerRef.current) clearInterval(traceTimerRef.current);
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, []);

  // ── Sync Elements with Dagre Layout & Staggered Reveal ────────────────────
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const role = getRole();

    cy.batch(() => {
      // Clear all past elements to prevent ANY stale nodes from earlier transactions
      cy.elements().remove();

      // Add Nodes
      nodes.forEach((item) => {
        const nodeId = String(item.accountId || item.account_id || item.id || '');
        if (!nodeId) return;
        const displayLabel = role === 'admin' ? nodeId : maskAccount(nodeId);

        cy.add({
          group: 'nodes',
          data: {
            ...item,
            id: nodeId,
            displayLabel,
            status: item.status || 'active',
            type: item.type || item.node_type || item.account_type || 'mule',
            layer: item.layer !== undefined ? item.layer : 0,
            risk_score: item.risk_score !== undefined ? item.risk_score : 75
          }
        });
      });

      // Add Edges
      edges.forEach((edge, idx) => {
        const edgeId = String(edge.id || edge.tx_id || `e-${idx}`);
        const sourceId = String(edge.source || edge.from || '');
        const targetId = String(edge.target || edge.to || '');

        if (!sourceId || !targetId) return;
        if (!cy.getElementById(sourceId).length || !cy.getElementById(targetId).length) return;

        const isSusp = Boolean(edge.is_suspicious || edge.suspicious || Number(edge.amount || 0) > 80000);

        const addedEdge = cy.add({
          group: 'edges',
          data: {
            ...edge,
            id: edgeId,
            source: sourceId,
            target: targetId,
            amount: Number(edge.amount || 0),
            channel: edge.channel || 'UPI',
            label: formatEdgeLabel(edge),
            is_suspicious: isSusp,
            hop_number: edge.hop_number || 1,
            total_hops: edge.total_hops || 1
          }
        });

        if (isSusp) {
          addedEdge.addClass('suspicious-edge');
        }
      });
    });

    if (nodes.length > 0) {
      runLayout(cy, false);
    }
  }, [nodes, edges, runLayout]);

  return (
    <div
      className="relative w-full h-full overflow-hidden select-none bg-[#060B14]"
      style={{
        backgroundImage: 'radial-gradient(rgba(56, 189, 248, 0.16) 1.2px, transparent 1.2px)',
        backgroundSize: '24px 24px',
        boxShadow: 'inset 0 0 140px rgba(2, 6, 18, 0.95)'
      }}
    >
      {/* Cytoscape mount container */}
      <div
        ref={containerRef}
        className="graph-canvas w-full h-full relative z-10"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', background: 'transparent' }}
      />

      {/* Professional Empty State Overlay */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-[#060B14]/90 backdrop-blur-sm select-none">
          <div className="p-6 rounded-xl bg-[#081120] border border-[#1E3A5F] text-center max-w-sm shadow-[0_8px_32px_rgba(0,0,0,0.7)]">
            <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center mx-auto mb-3">
              <Network className="w-5 h-5 text-sky-400 animate-pulse" />
            </div>
            <div className="text-xs font-mono font-bold text-slate-100 uppercase tracking-wider mb-1">
              NO INVESTIGATION GRAPH AVAILABLE
            </div>
            <div className="text-[11px] font-mono text-slate-400">
              No connected transaction relationships recorded for this entity.
            </div>
          </div>
        </div>
      )}

      {/* Floating Investigation HUD Controls (Top-Left - Matching Reference) */}
      <div className="absolute top-4 left-4 z-30 flex items-center gap-1.5 bg-[#081120]/90 border border-[#1E3A5F] px-2.5 py-1.5 rounded-lg shadow-[0_8px_32px_rgba(0,0,0,0.7)] backdrop-blur-md font-mono select-none">
        <button
          onClick={handleZoomIn}
          className="p-1.5 rounded-md text-sky-400 hover:text-white hover:bg-sky-950/60 transition-all"
          title="Zoom In"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-1.5 rounded-md text-sky-400 hover:text-white hover:bg-sky-950/60 transition-all"
          title="Zoom Out"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <div className="w-px h-4 bg-[#1E3A5F] mx-0.5" />
        <button
          onClick={handleFit}
          className="p-1.5 rounded-md text-sky-400 hover:text-white hover:bg-sky-950/60 transition-all"
          title="Fit View"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleResetLayout}
          className="p-1.5 rounded-md text-sky-400 hover:text-white hover:bg-sky-950/60 transition-all"
          title="Reset Layout (DAG)"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Dynamic Topology Label Badge (Top-Right - Matching Reference) */}
      <div className="absolute top-4 right-4 z-30 bg-[#081120]/90 border border-[#1E3A5F] px-3.5 py-1.5 rounded-lg shadow-[0_8px_32px_rgba(0,0,0,0.7)] backdrop-blur-md font-mono select-none flex items-center gap-2">
        <span className="text-[10px] text-sky-400 font-extrabold uppercase tracking-wide">TOPOLOGY:</span>
        <span className="text-[10px] text-slate-100 font-semibold">{topologyLabel}</span>
      </div>

      {/* Lower-Left Entity Geometries Legend (Matching Reference) */}
      <EntityLegend />

      {/* Lower-Left Selected Entity HUD Card (Matching Reference) */}
      <SelectedEntityHUDCard nodeData={leadNodeData} />


    </div>
  );
});

GraphCanvas.displayName = 'GraphCanvas';
export default React.memo(GraphCanvas);
