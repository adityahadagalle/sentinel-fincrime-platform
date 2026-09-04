import React, { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react';
import cytoscape from 'cytoscape';
import { graphStyles } from './graphStyles';
import { getRole } from '../../roleStore';
import { maskAccount } from '../../utils/maskAccount';

// ── ANIMATION TIMING (ms) ─────────────────────────────────────────────────────
// These constants control the pacing of the progressive reveal.
// Tuned for a deliberate, forensic-investigation feel.
const TIMING = {
  rootNodeReveal:     650,  // pause after the first (root) node appears before edges start
  hopTransitionDelay: 350,  // gap before each new edge begins drawing
  edgeDrawDuration:  1600,  // total canvas edge-stroke + particle animation duration
  nodeArrivalPause:   500,  // pause after a destination node's arrival pulse
};

// ── EDGE LABEL FORMATTER ──────────────────────────────────────────────────────
const formatTransactionLabel = (edge) => {
  const amount = Number(edge.amount || 0);
  const formattedAmount = new Intl.NumberFormat('en-IN').format(Math.round(amount));
  const channel = edge.channel || 'UPI';
  const hopStr = edge.total_hops > 1
    ? ` \u00B7 H${edge.hop_number || 1}/${edge.total_hops}`
    : (edge.hop_number > 1 ? ` \u00B7 H${edge.hop_number}` : '');
  return `\u20B9${formattedAmount} \u00B7 ${channel}${hopStr}`;
};

// ── ROLE THEME HELPER ─────────────────────────────────────────────────────────
const getRoleTheme = (role = '') => {
  const r = String(role).toUpperCase();
  if (r.includes('VICTIM') || r.includes('ORIGIN') || r.includes('SOURCE')) {
    return { accent: '#38BDF8', bg: 'rgba(56,189,248,0.12)', border: 'rgba(56,189,248,0.4)', text: '#38BDF8' };
  }
  if (r.includes('MULE') || r.includes('SUSPECT')) {
    return { accent: '#F87171', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.4)', text: '#F87171' };
  }
  if (r.includes('MERCHANT') || r.includes('OUTLET')) {
    return { accent: '#34D399', bg: 'rgba(52,211,153,0.12)', border: 'rgba(52,211,153,0.4)', text: '#34D399' };
  }
  if (r.includes('UPI')) {
    return { accent: '#C084FC', bg: 'rgba(192,132,252,0.12)', border: 'rgba(192,132,252,0.4)', text: '#C084FC' };
  }
  if (r.includes('CASHOUT') || r.includes('CRYPTO') || r.includes('ATM')) {
    return { accent: '#FB7185', bg: 'rgba(251,113,133,0.12)', border: 'rgba(251,113,133,0.4)', text: '#FB7185' };
  }
  if (r.includes('HUB') || r.includes('COLLECTOR') || r.includes('INTERMEDIARY')) {
    return { accent: '#FBBF24', bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.4)', text: '#FBBF24' };
  }
  return { accent: '#94A3B8', bg: 'rgba(148,163,184,0.12)', border: 'rgba(148,163,184,0.4)', text: '#94A3B8' };
};

// ── HIERARCHICAL DAG LAYOUT ───────────────────────────────────────────────────
// Unchanged from the original — left-to-right column layout using hop/layer data.
const applyHierarchicalDagLayout = (cy, nodes, edges) => {
  if (!cy || cy.nodes().length === 0) return;

  const cyNodes = cy.nodes();
  const cyEdges = cy.edges();

  const inDegree = {};
  const adj = {};
  cyNodes.forEach((n) => {
    const id = n.id();
    inDegree[id] = 0;
    adj[id] = [];
  });

  cyEdges.forEach((e) => {
    const src = e.source().id();
    const tgt = e.target().id();
    if (adj[src]) adj[src].push(tgt);
    if (inDegree[tgt] !== undefined) inDegree[tgt] += 1;
  });

  const rankMap = {};
  const queue = [];

  cyNodes.forEach((n) => {
    const id = n.id();
    const nodeLayer = n.data('layer');
    if (nodeLayer !== undefined && nodeLayer !== null && !isNaN(Number(nodeLayer))) {
      rankMap[id] = Number(nodeLayer);
    } else if (inDegree[id] === 0) {
      queue.push({ id, depth: 0 });
    }
  });

  if (queue.length === 0 && cyNodes.length > 0 && Object.keys(rankMap).length === 0) {
    queue.push({ id: cyNodes[0].id(), depth: 0 });
  }

  while (queue.length > 0) {
    const { id, depth } = queue.shift();
    if (rankMap[id] === undefined || depth > rankMap[id]) {
      rankMap[id] = depth;
      const neighbors = adj[id] || [];
      neighbors.forEach((nxt) => queue.push({ id: nxt, depth: depth + 1 }));
    }
  }

  const columns = {};
  cyNodes.forEach((n) => {
    const id = n.id();
    const r = rankMap[id] !== undefined ? rankMap[id] : 0;
    if (!columns[r]) columns[r] = [];
    columns[r].push(id);
  });

  const colKeys = Object.keys(columns).map(Number).sort((a, b) => a - b);

  const rankSep = 260;
  const nodeSep = 145;
  const startX = 120;
  const centerY = 360;

  colKeys.forEach((colKey, colIdx) => {
    const colNodeIds = columns[colKey];
    const totalInCol = colNodeIds.length;
    const startY = centerY - ((totalInCol - 1) * nodeSep) / 2;

    colNodeIds.forEach((id, rowIdx) => {
      const cyNode = cy.getElementById(id);
      if (cyNode.length > 0) {
        cyNode.position({
          x: startX + colIdx * rankSep,
          y: startY + rowIdx * nodeSep
        });
      }
    });
  });

  setTimeout(() => {
    if (cy && !cy.destroyed()) {
      cy.fit(cy.elements(), 70);
      if (cy.zoom() > 1.05) {
        cy.zoom(1.0);
        cy.center();
      }
    }
  }, 40);
};

// ── BFS REVEAL SEQUENCE BUILDER ───────────────────────────────────────────────
//
// Produces an ordered array of steps that describe the progressive reveal:
//
//   { type: 'node', id, isRoot }   — make this node visible
//   { type: 'edge', id, source, target } — animate + reveal this edge
//
// The ordering guarantees:
//   1. Root node(s) appear first.
//   2. For each node, its outgoing edges are animated sequentially (sorted by hop_number).
//   3. Each destination node appears *after* its incoming edge animation, not before.
//   4. Branching is handled naturally: branches are animated sequentially in BFS order.
//
const buildRevealSequence = (cy) => {
  if (!cy || cy.destroyed() || cy.nodes().length === 0) return [];

  const cyNodes = cy.nodes();
  const cyEdges = cy.edges();

  const outEdgeIds = {}; // nodeId → [edgeId]
  const inDegree   = {}; // nodeId → incoming edge count

  cyNodes.forEach((n) => {
    outEdgeIds[n.id()] = [];
    inDegree[n.id()] = 0;
  });

  cyEdges.forEach((e) => {
    const src = e.source().id();
    const tgt = e.target().id();
    if (outEdgeIds[src] !== undefined) outEdgeIds[src].push(e.id());
    if (inDegree[tgt]  !== undefined) inDegree[tgt]++;
  });

  // Root nodes = nodes with no incoming edges
  const roots = [];
  cyNodes.forEach((n) => {
    if (inDegree[n.id()] === 0) roots.push(n.id());
  });

  // Fallback: pick node with smallest layer value
  if (roots.length === 0 && cyNodes.length > 0) {
    let minLayer = Infinity;
    let minId = cyNodes[0].id();
    cyNodes.forEach((n) => {
      const l = Number(n.data('layer') || 0);
      if (l < minLayer) { minLayer = l; minId = n.id(); }
    });
    roots.push(minId);
  }

  const sequence      = [];
  const visitedNodes  = new Set();
  const visitedEdges  = new Set();
  const bfsQueue      = [];

  // Seed with root nodes
  roots.forEach((rootId) => {
    if (!visitedNodes.has(rootId)) {
      visitedNodes.add(rootId);
      sequence.push({ type: 'node', id: rootId, isRoot: true });
      bfsQueue.push(rootId);
    }
  });

  // BFS
  while (bfsQueue.length > 0) {
    const nodeId = bfsQueue.shift();

    // Sort outgoing edges by hop_number for deterministic reveal order
    const sortedEdgeIds = (outEdgeIds[nodeId] || []).slice().sort((a, b) => {
      const ea = cy.getElementById(a);
      const eb = cy.getElementById(b);
      const ha = ea.length > 0 ? (ea.data('hop_number') || 1) : 1;
      const hb = eb.length > 0 ? (eb.data('hop_number') || 1) : 1;
      return ha - hb;
    });

    for (const edgeId of sortedEdgeIds) {
      if (visitedEdges.has(edgeId)) continue;
      visitedEdges.add(edgeId);

      const edge = cy.getElementById(edgeId);
      if (!edge.length) continue;
      const targetId = edge.target().id();

      // Edge animation step (always added, even if target already visited)
      sequence.push({ type: 'edge', id: edgeId, source: nodeId, target: targetId });

      // Destination node step (only if first time we reach this node)
      if (!visitedNodes.has(targetId)) {
        visitedNodes.add(targetId);
        sequence.push({ type: 'node', id: targetId, isRoot: false });
        bfsQueue.push(targetId);
      }
    }
  }

  return sequence;
};

// ── CANVAS EDGE DRAWING ────────────────────────────────────────────────────────
//
// Draws one frame of the animated edge reveal onto the 2D canvas context.
//
// The context must already have the DPR transform applied (via setTransform).
// srcPos / tgtPos are in CSS pixel space (from Cytoscape renderedPosition()).
// progress ∈ [0, 1] — how far along the edge the particle/stroke has traveled.
//
// Visuals:
//   - A growing stroke from source → tip (matching Cytoscape's bezier curve approx.)
//   - A glowing particle dot at the tip representing the money in transit
//   - Dashed stroke for suspicious edges, solid for normal
//   - Color: #EF4444 (suspicious) or #38BDF8 (normal) — inherits existing semantics
//
const drawEdgeFrame = (ctx, srcPos, tgtPos, progress, isSuspicious) => {
  if (progress <= 0) return;

  const color     = isSuspicious ? '#EF4444' : '#38BDF8';
  const lineWidth = isSuspicious ? 3.5 : 2.5;

  // Approximate Cytoscape's bezier control point.
  // Cytoscape uses control-point-step-size: 60; we use a 28px perpendicular
  // offset in rendered space to get a visually matching curve.
  const dx   = tgtPos.x - srcPos.x;
  const dy   = tgtPos.y - srcPos.y;
  const len  = Math.sqrt(dx * dx + dy * dy) || 1;
  const perpX = (-dy / len) * 28;
  const perpY = ( dx / len) * 28;
  const cpX = (srcPos.x + tgtPos.x) / 2 + perpX;
  const cpY = (srcPos.y + tgtPos.y) / 2 + perpY;

  const t     = Math.max(0, Math.min(1, progress));
  const steps = 80; // bezier sample count

  ctx.save();

  // ── Growing stroke from source to current tip ────────────────────────────
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth   = lineWidth;
  ctx.lineCap     = 'round';
  ctx.lineJoin    = 'round';
  ctx.globalAlpha = 0.85;
  if (isSuspicious) ctx.setLineDash([8, 4]);

  let first = true;
  for (let i = 0; i <= steps; i++) {
    const u  = (i / steps) * t;
    const mu = 1 - u;
    const px = mu * mu * srcPos.x + 2 * mu * u * cpX + u * u * tgtPos.x;
    const py = mu * mu * srcPos.y + 2 * mu * u * cpY + u * u * tgtPos.y;
    if (first) { ctx.moveTo(px, py); first = false; }
    else         ctx.lineTo(px, py);
  }
  ctx.stroke();
  ctx.setLineDash([]);

  // ── Particle (money in transit) at the stroke tip ────────────────────────
  const mu = 1 - t;
  const px = mu * mu * srcPos.x + 2 * mu * t * cpX + t * t * tgtPos.x;
  const py = mu * mu * srcPos.y + 2 * mu * t * cpY + t * t * tgtPos.y;

  // Outer glow ring
  ctx.globalAlpha = 0.18;
  ctx.beginPath();
  ctx.arc(px, py, 12, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();

  // Mid glow
  ctx.globalAlpha = 0.40;
  ctx.beginPath();
  ctx.arc(px, py, 7.5, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();

  // Solid core particle
  ctx.globalAlpha = 1;
  ctx.beginPath();
  ctx.arc(px, py, 4.5, 0, Math.PI * 2);
  ctx.fillStyle   = color;
  ctx.shadowColor = color;
  ctx.shadowBlur  = 14;
  ctx.fill();
  ctx.shadowBlur  = 0;

  ctx.restore();
};

// ── REVEAL ANIMATION ENGINE ───────────────────────────────────────────────────
//
// Manages the full lifecycle of the progressive graph reveal.
//
// Design principles:
//   - All real Cytoscape elements are added normally; this function only
//     controls their visibility via the 'reveal-hidden' class.
//   - A transparent <canvas> overlay draws the animated stroke + particle
//     during each edge animation. The real Cytoscape edge stays hidden until
//     the animation completes, then appears while the canvas is cleared.
//   - The animation is fully cancellable and cleans up all timers / RAF ids.
//   - After completion, all reveal-* classes are removed so the full graph
//     is interactable as normal.
//
const startRevealAnimation = (cy, canvasEl, animStateRef) => {
  if (!cy || cy.destroyed() || !canvasEl) return;

  // Cancel any running animation first
  if (animStateRef.current?.cancel) {
    animStateRef.current.cancel();
  }

  const ctx       = canvasEl.getContext('2d');
  let   cancelled = false;
  let   rafId     = null;
  const timeoutIds = [];

  // ── Cancellation ──────────────────────────────────────────────────────────
  const cancel = () => {
    cancelled = true;
    if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
    timeoutIds.forEach(clearTimeout);
    timeoutIds.length = 0;
    doClearCanvas();
    // Ensure all elements are fully visible after cancellation
    if (cy && !cy.destroyed()) {
      cy.elements().removeClass('reveal-hidden node-arriving');
    }
  };
  animStateRef.current = { cancel };

  // ── Canvas helpers ────────────────────────────────────────────────────────

  // Resize canvas to match its container (handles window resize / initial sizing).
  // Always resets the DPR transform so drawing coordinates match CSS pixel space.
  const resizeCanvas = () => {
    const container = canvasEl.parentElement;
    if (!container) return;
    const rect  = container.getBoundingClientRect();
    const dpr   = window.devicePixelRatio || 1;
    const physW = Math.round(rect.width  * dpr);
    const physH = Math.round(rect.height * dpr);
    if (canvasEl.width !== physW || canvasEl.height !== physH) {
      canvasEl.width  = physW;
      canvasEl.height = physH;
      canvasEl.style.width  = rect.width  + 'px';
      canvasEl.style.height = rect.height + 'px';
    }
    // setTransform is idempotent — safe to call every frame
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };

  const doClearCanvas = () => {
    if (!canvasEl.parentElement) return;
    resizeCanvas();
    const dpr = window.devicePixelRatio || 1;
    ctx.clearRect(0, 0, canvasEl.width / dpr, canvasEl.height / dpr);
  };

  // ── Promise helpers ───────────────────────────────────────────────────────
  const delay = (ms) =>
    new Promise((resolve) => {
      if (cancelled) { resolve(); return; }
      const id = setTimeout(resolve, ms);
      timeoutIds.push(id);
    });

  // Animate a single edge stroke + particle using requestAnimationFrame.
  // Positions are re-read every frame so pan/zoom during animation stays correct.
  const animateEdge = (sourceId, targetId, isSuspicious, durationMs) =>
    new Promise((resolve) => {
      if (cancelled) { resolve(); return; }
      const startTime = performance.now();

      const draw = (now) => {
        if (cancelled) { rafId = null; resolve(); return; }

        resizeCanvas();
        const dpr  = window.devicePixelRatio || 1;
        const cssW = canvasEl.width  / dpr;
        const cssH = canvasEl.height / dpr;
        ctx.clearRect(0, 0, cssW, cssH);

        const srcNode = cy.getElementById(sourceId);
        const tgtNode = cy.getElementById(targetId);
        if (!srcNode.length || !tgtNode.length) { rafId = null; resolve(); return; }

        const srcPos = srcNode.renderedPosition();
        const tgtPos = tgtNode.renderedPosition();

        const elapsed = now - startTime;
        const rawP    = Math.min(elapsed / durationMs, 1);

        // Cubic ease-in-out for natural, deliberate motion
        const progress = rawP < 0.5
          ? 4 * rawP * rawP * rawP
          : 1 - Math.pow(-2 * rawP + 2, 3) / 2;

        drawEdgeFrame(ctx, srcPos, tgtPos, progress, isSuspicious);

        if (rawP < 1) {
          rafId = requestAnimationFrame(draw);
        } else {
          rafId = null;
          resolve();
        }
      };

      rafId = requestAnimationFrame(draw);
    });

  // ── Main async reveal loop ────────────────────────────────────────────────
  const run = async () => {
    // Step 0: hide everything and clear any existing highlight state
    cy.elements()
      .removeClass('path-highlight dimmed new-transaction-pulse node-arriving')
      .addClass('reveal-hidden');

    const sequence = buildRevealSequence(cy);
    if (!sequence.length || cancelled) {
      // Nothing to animate — just reveal all
      cy.elements().removeClass('reveal-hidden');
      return;
    }

    for (const step of sequence) {
      if (cancelled) break;

      // ── NODE REVEAL STEP ──────────────────────────────────────────────────
      if (step.type === 'node') {
        const node = cy.getElementById(step.id);
        if (!node.length) continue;

        // Reveal: removing reveal-hidden triggers Cytoscape's opacity transition (~200ms fade-in)
        node.removeClass('reveal-hidden').addClass('node-arriving');

        if (step.isRoot) {
          // Let the root node settle visually before the first edge draws
          await delay(TIMING.rootNodeReveal);
        } else {
          // Destination node: wait for arrival pulse to register
          await delay(TIMING.nodeArrivalPause);
        }

        // Schedule removal of the arriving class (non-blocking — runs in background)
        if (!cancelled) {
          const nRef = node;
          const tid  = setTimeout(() => {
            if (!cy.destroyed()) nRef.removeClass('node-arriving');
          }, 650);
          timeoutIds.push(tid);
        }

      // ── EDGE ANIMATION STEP ───────────────────────────────────────────────
      } else if (step.type === 'edge') {
        if (cancelled) break;

        const edge = cy.getElementById(step.id);
        if (!edge.length) continue;

        // Brief pause before edge starts drawing (creates the "and then…" cadence)
        await delay(TIMING.hopTransitionDelay);
        if (cancelled) break;

        const isSuspicious = !!edge.data('suspicious');

        // ── Animate canvas stroke + particle ─────────────────────────────
        // During this time: the real Cytoscape edge stays hidden (reveal-hidden).
        // The canvas overlay shows the growing stroke and particle instead.
        await animateEdge(step.source, step.target, isSuspicious, TIMING.edgeDrawDuration);
        if (cancelled) break;

        // ── Particle arrives: reveal real edge, clear canvas overlay ──────
        edge.removeClass('reveal-hidden');
        doClearCanvas();
        // (destination node reveal is the very next step in the sequence)
      }
    }

    // Animation complete — ensure all elements are visible and clean up
    if (!cancelled) {
      cy.elements().removeClass('reveal-hidden node-arriving');
      doClearCanvas();
      animStateRef.current = null;
    }
  };

  run().catch(() => {
    // Suppress unhandled promise rejections (e.g., if cy is destroyed mid-run)
  });
};

// ── GRAPH CANVAS COMPONENT ────────────────────────────────────────────────────
const GraphCanvas = forwardRef(({ nodes = [], edges = [], onNodeClick, onEdgeClick, onSelectionChange }, ref) => {
  const containerRef      = useRef(null);
  const canvasOverlayRef  = useRef(null);
  const cyRef             = useRef(null);
  const isInitializedRef  = useRef(false);
  const onNodeClickRef    = useRef(onNodeClick);
  const onEdgeClickRef    = useRef(onEdgeClick);
  const onSelectionChangeRef = useRef(onSelectionChange);
  const traceTimerRef     = useRef(null);
  const animStateRef      = useRef(null);   // { cancel: fn } — current animation handle
  const pendingAnimStartRef = useRef(null); // setTimeout id for the delayed animation kick-off
  const activeSelectionRef  = useRef(null); // { type: 'node' | 'edge', id: string } pinned on click

  const [tooltip, setTooltip] = useState(null);

  // Keep callback refs up to date without re-running effects
  useEffect(() => {
    onNodeClickRef.current    = onNodeClick;
    onEdgeClickRef.current    = onEdgeClick;
    onSelectionChangeRef.current = onSelectionChange;
  }, [onNodeClick, onEdgeClick, onSelectionChange]);

  // ── Imperative API (unchanged from original + restartAnimation) ───────────
  useImperativeHandle(ref, () => ({
    fit: () => {
      if (cyRef.current) {
        cyRef.current.fit(cyRef.current.elements(), 60);
        if (cyRef.current.zoom() > 1.05) {
          cyRef.current.zoom(1.0);
          cyRef.current.center();
        }
      }
    },
    reset: () => {
      if (cyRef.current) {
        cyRef.current.reset();
        applyHierarchicalDagLayout(cyRef.current, nodes, edges);
      }
    },
    zoomIn: () => {
      if (cyRef.current) {
        cyRef.current.zoom({
          level: cyRef.current.zoom() * 1.25,
          renderedPosition: {
            x: containerRef.current.clientWidth  / 2,
            y: containerRef.current.clientHeight / 2
          }
        });
      }
    },
    zoomOut: () => {
      if (cyRef.current) {
        cyRef.current.zoom({
          level: cyRef.current.zoom() * 0.8,
          renderedPosition: {
            x: containerRef.current.clientWidth  / 2,
            y: containerRef.current.clientHeight / 2
          }
        });
      }
    },
    centerOn: (id) => {
      const cy = cyRef.current;
      if (!cy) return;
      const ele = cy.getElementById(String(id));
      if (ele.length > 0) {
        cy.center(ele);
        cy.zoom({
          level: 1.3,
          renderedPosition: {
            x: containerRef.current.clientWidth  / 2,
            y: containerRef.current.clientHeight / 2
          }
        });
      }
    },
    clearHighlight: () => {
      const cy = cyRef.current;
      if (!cy) return;
      if (traceTimerRef.current) {
        clearInterval(traceTimerRef.current);
        traceTimerRef.current = null;
      }
      activeSelectionRef.current = null;
      cy.elements().removeClass('path-highlight dimmed new-transaction-pulse node-hovered flow-incoming flow-outgoing node-flow-source node-flow-target edge-hovered');
      onSelectionChangeRef.current?.(null);
      setTooltip(null);
    },
    tracePath: (onStepCallback, onCompleteCallback) => {
      const cy = cyRef.current;
      if (!cy) return;

      if (traceTimerRef.current) {
        clearInterval(traceTimerRef.current);
        traceTimerRef.current = null;
      }

      cy.elements().removeClass('path-highlight dimmed');
      const sortedEdges = cy.edges().sort(
        (a, b) => (a.data('hop_number') || 1) - (b.data('hop_number') || 1)
      );

      if (sortedEdges.length === 0) return;

      cy.elements().addClass('dimmed');
      let stepIndex = 0;

      traceTimerRef.current = setInterval(() => {
        if (stepIndex >= sortedEdges.length) {
          clearInterval(traceTimerRef.current);
          traceTimerRef.current = null;
          onCompleteCallback?.();
          return;
        }

        const currentEdge = sortedEdges[stepIndex];
        const sourceNode  = currentEdge.source();
        const targetNode  = currentEdge.target();

        currentEdge.removeClass('dimmed').addClass('path-highlight');
        sourceNode.removeClass('dimmed').addClass('path-highlight');
        targetNode.removeClass('dimmed').addClass('path-highlight');

        onStepCallback?.({
          step:       stepIndex + 1,
          totalSteps: sortedEdges.length,
          edgeId:     currentEdge.id(),
          source:     sourceNode.id(),
          target:     targetNode.id(),
          amount:     currentEdge.data('amount'),
          hop:        currentEdge.data('hop_number') || (stepIndex + 1)
        });

        stepIndex++;
      }, 450);
    },
    // New: allows GraphModule to trigger a replay from outside
    restartAnimation: () => {
      const cy = cyRef.current;
      if (cy && !cy.destroyed()) {
        startRevealAnimation(cy, canvasOverlayRef.current, animStateRef);
      }
    }
  }));

  // ── 1. Cytoscape Initialization (runs once) ───────────────────────────────
  useEffect(() => {
    if (!containerRef.current || isInitializedRef.current) return;

    const cy = cytoscape({
      container:          containerRef.current,
      elements:           [],
      style:              graphStyles,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false
    });

    cyRef.current        = cy;
    isInitializedRef.current = true;

    // ── Hover: Node (Precision Money Flow Isolation) ────────────────────────
    cy.on('mouseover', 'node', (evt) => {
      const node = evt.target;
      // Hidden nodes during reveal must not trigger hover
      if (node.hasClass('reveal-hidden')) return;

      // 1. Clear previous transient hover styles
      cy.elements().removeClass('node-hovered flow-incoming flow-outgoing node-flow-source node-flow-target edge-hovered');

      // 2. Identify ONLY immediate incoming and outgoing relationships
      const inEdges     = node.incomers('edge');
      const outEdges    = node.outgoers('edge');
      const sourceNodes = inEdges.sources();
      const targetNodes = outEdges.targets();

      const immediateConnected = node.union(inEdges).union(outEdges).union(sourceNodes).union(targetNodes);
      const otherElements      = cy.elements().difference(immediateConnected);

      // 3. Apply precision hover styles
      node.addClass('node-hovered');
      inEdges.addClass('flow-incoming');
      outEdges.addClass('flow-outgoing');
      sourceNodes.addClass('node-flow-source');
      targetNodes.addClass('node-flow-target');

      // Dim all unrelated graph elements
      otherElements.addClass('dimmed');
      immediateConnected.removeClass('dimmed');

      // 4. Extract authentic metadata directly from existing data
      const data = node.data();
      const pos  = evt.renderedPosition;

      const incomingFlows = inEdges.map(e => ({
        id:         e.data('tx_id') || e.id(),
        source:     e.data('source') || e.data('from') || e.source().id(),
        amount:     Number(e.data('amount') || 0),
        channel:    e.data('channel') || 'UPI',
        hop:        e.data('hop_number') || 1,
        suspicious: !!e.data('suspicious')
      }));

      const outgoingFlows = outEdges.map(e => ({
        id:         e.data('tx_id') || e.id(),
        target:     e.data('target') || e.data('to') || e.target().id(),
        amount:     Number(e.data('amount') || 0),
        channel:    e.data('channel') || 'UPI',
        hop:        e.data('hop_number') || 1,
        suspicious: !!e.data('suspicious')
      }));

      const totalInboundAmt  = incomingFlows.reduce((sum, f) => sum + f.amount, 0);
      const totalOutboundAmt = outgoingFlows.reduce((sum, f) => sum + f.amount, 0);

      // Clamping within container boundaries
      const cWidth  = containerRef.current?.clientWidth  || 1000;
      const cHeight = containerRef.current?.clientHeight || 700;
      let tx = pos.x + 20;
      let ty = pos.y - 20;
      if (tx + 320 > cWidth)  tx = Math.max(12, pos.x - 325);
      if (ty + 320 > cHeight) ty = Math.max(12, cHeight - 330);
      if (ty < 12) ty = 12;

      setTooltip({
        type:          'node',
        x:             tx,
        y:             ty,
        id:            data.accountId || data.id,
        displayLabel:  data.displayLabel || data.accountId || data.id,
        entityType:    (data.node_type || data.account_type || 'ACCOUNT').toUpperCase(),
        layer:         data.layer !== undefined ? data.layer : 0,
        status:        data.status || 'ACTIVE',
        riskScore:     data.risk_score !== undefined ? data.risk_score : null,
        balance:       data.balance || data.current_balance_sim || null,
        incomingFlows,
        outgoingFlows,
        totalInbound:  totalInboundAmt  || data.total_inbound  || 0,
        totalOutbound: totalOutboundAmt || data.total_outbound || 0
      });
    });

    // ── Hover: Edge (Detailed Transaction Inspection) ───────────────────────
    cy.on('mouseover', 'edge', (evt) => {
      const edge = evt.target;
      if (edge.hasClass('reveal-hidden')) return;

      cy.elements().removeClass('node-hovered flow-incoming flow-outgoing node-flow-source node-flow-target edge-hovered');

      const sourceNode = edge.source();
      const targetNode = edge.target();
      const immediate  = edge.union(sourceNode).union(targetNode);
      const otherElements = cy.elements().difference(immediate);

      edge.addClass('edge-hovered');
      sourceNode.addClass('node-flow-source');
      targetNode.addClass('node-flow-target');

      otherElements.addClass('dimmed');
      immediate.removeClass('dimmed');

      const data = edge.data();
      const pos  = evt.renderedPosition;

      const cWidth  = containerRef.current?.clientWidth  || 1000;
      const cHeight = containerRef.current?.clientHeight || 700;
      let tx = pos.x + 20;
      let ty = pos.y - 20;
      if (tx + 300 > cWidth)  tx = Math.max(12, pos.x - 305);
      if (ty + 260 > cHeight) ty = Math.max(12, cHeight - 270);
      if (ty < 12) ty = 12;

      setTooltip({
        type:       'edge',
        x:          tx,
        y:          ty,
        id:         data.tx_id || data.id,
        from:       data.source || data.from || sourceNode.id(),
        to:         data.target || data.to || targetNode.id(),
        amount:     data.amount     || 0,
        channel:    data.channel    || 'UPI',
        hop:        data.hop_number || 1,
        totalHops:  data.total_hops || 1,
        riskScore:  data.risk_score !== undefined ? data.risk_score : null,
        status:     data.status || null,
        timestamp:  data.timestamp || null,
        suspicious: !!data.suspicious
      });
    });

    // ── Mouseout: Node & Edge ───────────────────────────────────────────────
    cy.on('mouseout', 'node edge', () => {
      cy.elements().removeClass('node-hovered flow-incoming flow-outgoing node-flow-source node-flow-target edge-hovered');

      // If a selection was tapped/pinned, restore that selection; otherwise undim all
      if (activeSelectionRef.current) {
        const sel = activeSelectionRef.current;
        const ele = cy.getElementById(sel.id);
        if (ele.length > 0) {
          if (sel.type === 'node') {
            const pathElements = ele.successors().union(ele.predecessors()).union(ele);
            pathElements.addClass('path-highlight').removeClass('dimmed');
            cy.elements().difference(pathElements).addClass('dimmed');
          } else {
            const src = ele.source();
            const pathElements = src.successors().union(src.predecessors()).union(src).union(ele);
            pathElements.addClass('path-highlight').removeClass('dimmed');
            cy.elements().difference(pathElements).addClass('dimmed');
          }
        } else {
          cy.elements().removeClass('dimmed');
        }
      } else {
        cy.elements().removeClass('dimmed');
      }

      setTooltip(null);
    });

    // ── Click: Node ─────────────────────────────────────────────────────────
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      if (node.hasClass('reveal-hidden')) return;
      activeSelectionRef.current = { type: 'node', id: node.id() };
      cy.elements().removeClass('path-highlight dimmed node-hovered flow-incoming flow-outgoing node-flow-source node-flow-target edge-hovered');

      const pathElements = node.successors().union(node.predecessors()).union(node);
      pathElements.addClass('path-highlight');
      cy.elements().difference(pathElements).addClass('dimmed');

      const edgeCount = pathElements.edges().length;
      onSelectionChangeRef.current?.({ type: 'node', id: node.id(), hops: edgeCount || 1 });
      onNodeClickRef.current?.(node.data());
    });

    // ── Click: Edge ─────────────────────────────────────────────────────────
    cy.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      if (edge.hasClass('reveal-hidden')) return;
      activeSelectionRef.current = { type: 'edge', id: edge.id() };
      cy.elements().removeClass('path-highlight dimmed node-hovered flow-incoming flow-outgoing node-flow-source node-flow-target edge-hovered');

      const sourceNode   = edge.source();
      const pathElements = sourceNode.successors()
        .union(sourceNode.predecessors())
        .union(sourceNode)
        .union(edge);
      pathElements.addClass('path-highlight');
      cy.elements().difference(pathElements).addClass('dimmed');

      onSelectionChangeRef.current?.({
        type: 'edge',
        id:   edge.id(),
        hops: edge.data('total_hops') || 1
      });
      onEdgeClickRef.current?.(edge.data());
    });

    // ── Click: Background (deselect) ─────────────────────────────────────────
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        activeSelectionRef.current = null;
        cy.elements().removeClass('path-highlight dimmed node-hovered flow-incoming flow-outgoing node-flow-source node-flow-target edge-hovered');
        onSelectionChangeRef.current?.(null);
        onNodeClickRef.current?.(null);
        onEdgeClickRef.current?.(null);
        setTooltip(null);
      }
    });

    // ── Cleanup ──────────────────────────────────────────────────────────────
    return () => {
      if (animStateRef.current?.cancel) {
        animStateRef.current.cancel();
        animStateRef.current = null;
      }
      if (pendingAnimStartRef.current) {
        clearTimeout(pendingAnimStartRef.current);
        pendingAnimStartRef.current = null;
      }
      if (traceTimerRef.current) {
        clearInterval(traceTimerRef.current);
      }
      cyRef.current?.destroy();
      cyRef.current        = null;
      isInitializedRef.current = false;
    };
  }, []);

  // ── 2. Data Sync + Reveal Animation Trigger ───────────────────────────────
  //
  // Whenever nodes/edges change (new investigation loaded):
  //   a. Cancel any running reveal animation and pending start timer.
  //   b. Sync Cytoscape elements (add/update/remove — same logic as before).
  //   c. Apply the hierarchical layout.
  //   d. After a short settle delay, start the reveal animation.
  //
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !isInitializedRef.current) return;

    // Cancel running animation & pending start
    if (animStateRef.current?.cancel) {
      animStateRef.current.cancel();
      animStateRef.current = null;
    }
    if (pendingAnimStartRef.current) {
      clearTimeout(pendingAnimStartRef.current);
      pendingAnimStartRef.current = null;
    }

    // Sync graph data
    cy.batch(() => {
      const role       = getRole();
      const currentIds = new Set();

      nodes.forEach((item) => {
        const nodeId       = String(item.accountId || item.id);
        currentIds.add(nodeId);
        const displayLabel = role === 'admin' ? nodeId : maskAccount(nodeId);

        const existing = cy.getElementById(nodeId);
        if (existing.length > 0) {
          existing.data({ ...item, displayLabel });
        } else {
          cy.add({ data: { ...item, id: nodeId, displayLabel } });
        }
      });

      edges.forEach((edge) => {
        const edgeId = String(
          edge.id || edge.tx_id ||
          `${edge.source || edge.from}-${edge.target || edge.to}`
        );
        currentIds.add(edgeId);

        const existing = cy.getElementById(edgeId);
        if (existing.length > 0) {
          existing.data({ ...edge, label: edge.label || formatTransactionLabel(edge) });
        } else {
          cy.add({
            data: {
              ...edge,
              id:     edgeId,
              source: String(edge.source || edge.from),
              target: String(edge.target || edge.to),
              label:  edge.label || formatTransactionLabel(edge)
            }
          });
          // Note: new-transaction-pulse is intentionally omitted here.
          // The reveal animation provides a far richer visual introduction
          // for all new edges, so the standalone pulse is unnecessary.
        }
      });

      // Remove stale elements
      cy.elements().forEach((ele) => {
        if (!currentIds.has(ele.id())) ele.remove();
      });
    });

    if (nodes.length > 0) {
      applyHierarchicalDagLayout(cy, nodes, edges);

      // Wait for layout to settle (applyHierarchicalDagLayout has a 40ms internal
      // timeout for cy.fit; we add a bit more margin for the canvas to render).
      pendingAnimStartRef.current = setTimeout(() => {
        pendingAnimStartRef.current = null;
        if (cy && !cy.destroyed()) {
          startRevealAnimation(cy, canvasOverlayRef.current, animStateRef);
        }
      }, 120);
    }
  }, [nodes, edges]);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="relative w-full h-full">

      {/* Cytoscape host element */}
      <div
        ref={containerRef}
        className="graph-canvas"
        style={{
          width:      '100%',
          height:     '100%',
          background: '#0B132B',
          textAlign:  'left'
        }}
      />

      {/*
        Animation overlay canvas.
        – pointer-events: none so it never intercepts Cytoscape mouse events.
        – z-index: 10 so it sits above Cytoscape's own canvas layers.
        – Completely transparent when no animation is running.
        – Sized/resized dynamically inside startRevealAnimation.
      */}
      <canvas
        ref={canvasOverlayRef}
        style={{
          position:      'absolute',
          top:           0,
          left:          0,
          width:         '100%',
          height:        '100%',
          pointerEvents: 'none',
          zIndex:        10
        }}
      />

      {/* ── FLOATING HOVER TOOLTIP POPOVER (Enterprise Financial Investigation Card) ── */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-50 bg-[#0A0F1D]/95 border border-slate-700/80 rounded-lg p-3 shadow-2xl backdrop-blur-md font-mono text-[11px] text-slate-200 min-w-[270px] max-w-[320px] transition-opacity duration-150"
          style={{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }}
        >
          {tooltip.type === 'node' ? (() => {
            const theme = getRoleTheme(tooltip.entityType);
            const inCount = tooltip.incomingFlows?.length || 0;
            const outCount = tooltip.outgoingFlows?.length || 0;
            return (
              <div className="space-y-2.5">
                {/* Header: Entity ID & Role Badge */}
                <div className="flex items-center justify-between gap-3 pb-2 border-b border-slate-800">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: theme.accent }} />
                    <span className="font-['JetBrains_Mono'] text-[11px] font-bold text-slate-100 truncate">
                      {tooltip.id}
                    </span>
                  </div>
                  <span
                    className="text-[9px] font-['JetBrains_Mono'] font-bold uppercase px-2 py-0.5 rounded-sm border shrink-0"
                    style={{ background: theme.bg, borderColor: theme.border, color: theme.text }}
                  >
                    {tooltip.entityType}
                  </span>
                </div>

                {/* Status & Risk Indicators */}
                <div className="flex items-center justify-between text-[10px] bg-slate-900/80 px-2.5 py-1.5 rounded border border-slate-800/80">
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-400 font-sans text-[9px] uppercase tracking-wider">STATUS:</span>
                    <span className="font-['JetBrains_Mono'] text-slate-200 font-semibold uppercase">{tooltip.status}</span>
                  </div>
                  {tooltip.riskScore !== null && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400 font-sans text-[9px] uppercase tracking-wider">RISK:</span>
                      <span className={`font-['JetBrains_Mono'] font-bold ${
                        tooltip.riskScore >= 70 ? 'text-red-400' : tooltip.riskScore >= 40 ? 'text-amber-400' : 'text-emerald-400'
                      }`}>
                        {Math.round(tooltip.riskScore)}/100
                      </span>
                    </div>
                  )}
                </div>

                {/* Immediate Money Flow Summary */}
                <div className="space-y-2 pt-0.5">
                  {/* INCOMING FLOWS */}
                  <div className="rounded bg-[#06281D]/60 border border-emerald-900/50 p-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-sans font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1">
                        <span>↓</span> INCOMING ({inCount})
                      </span>
                      <span className="font-['JetBrains_Mono'] text-[11px] font-bold text-emerald-300">
                        ₹{Number(tooltip.totalInbound).toLocaleString('en-IN')}
                      </span>
                    </div>
                    {inCount > 0 ? (
                      <div className="space-y-1 max-h-24 overflow-y-auto pr-0.5 text-[9px] font-['JetBrains_Mono']">
                        {tooltip.incomingFlows.map((f, i) => (
                          <div key={i} className="flex items-center justify-between text-slate-300 pt-0.5 border-t border-emerald-900/30 first:border-none">
                            <span className="truncate max-w-[110px] text-slate-400" title={f.source}>{f.source}</span>
                            <div className="flex items-center gap-1.5 shrink-0">
                              <span className="text-slate-500 text-[8px]">{f.channel}</span>
                              <span className="text-emerald-300 font-semibold">₹{Number(f.amount).toLocaleString('en-IN')}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-[9px] font-sans text-slate-500 italic">Origin account (0 incoming)</div>
                    )}
                  </div>

                  {/* OUTGOING FLOWS */}
                  <div className="rounded bg-[#2B1704]/60 border border-amber-900/50 p-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] font-sans font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1">
                        <span>↑</span> OUTGOING ({outCount})
                      </span>
                      <span className="font-['JetBrains_Mono'] text-[11px] font-bold text-amber-300">
                        ₹{Number(tooltip.totalOutbound).toLocaleString('en-IN')}
                      </span>
                    </div>
                    {outCount > 0 ? (
                      <div className="space-y-1 max-h-24 overflow-y-auto pr-0.5 text-[9px] font-['JetBrains_Mono']">
                        {tooltip.outgoingFlows.map((f, i) => (
                          <div key={i} className="flex items-center justify-between text-slate-300 pt-0.5 border-t border-amber-900/30 first:border-none">
                            <span className="truncate max-w-[110px] text-slate-400" title={f.target}>{f.target}</span>
                            <div className="flex items-center gap-1.5 shrink-0">
                              <span className="text-slate-500 text-[8px]">{f.channel}</span>
                              <span className="text-amber-300 font-semibold">₹{Number(f.amount).toLocaleString('en-IN')}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-[9px] font-sans text-slate-500 italic">Terminal destination (0 outgoing)</div>
                    )}
                  </div>
                </div>
              </div>
            );
          })() : (
            <div className="space-y-2">
              {/* Header: Transaction ID & Flow Type Badge */}
              <div className="flex items-center justify-between gap-3 pb-1.5 border-b border-slate-800">
                <div className="flex items-center gap-1.5">
                  <span className="text-[9px] font-sans text-slate-500 uppercase tracking-wider font-semibold">TX</span>
                  <span className="font-['JetBrains_Mono'] text-[11px] font-bold text-sky-400">{tooltip.id}</span>
                </div>
                <span
                  className={`text-[9px] font-['JetBrains_Mono'] px-1.5 py-0.5 rounded font-bold border ${
                    tooltip.suspicious
                      ? 'bg-rose-950/80 text-rose-300 border-rose-600/50'
                      : 'bg-slate-900 text-slate-300 border-slate-700/50'
                  }`}
                >
                  {tooltip.suspicious ? 'SUSPICIOUS' : 'STANDARD'}
                </span>
              </div>

              {/* Path: FROM -> TO */}
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800/80 space-y-1">
                <div className="flex items-center justify-between text-[9px] font-sans text-slate-400 uppercase tracking-wider">
                  <span>SOURCE</span>
                  <span>DESTINATION</span>
                </div>
                <div className="flex items-center justify-between text-[10px] font-['JetBrains_Mono'] font-medium">
                  <span className="text-slate-200 truncate max-w-[105px]" title={tooltip.from}>{tooltip.from}</span>
                  <span className="text-slate-500 px-1">→</span>
                  <span className="text-slate-200 truncate max-w-[105px]" title={tooltip.to}>{tooltip.to}</span>
                </div>
              </div>

              {/* Amount */}
              <div className="flex items-baseline justify-between px-1">
                <span className="text-[9px] font-sans text-slate-400 uppercase tracking-wider">AMOUNT</span>
                <span className="font-['JetBrains_Mono'] text-[14px] font-bold text-emerald-400">
                  ₹{Number(tooltip.amount).toLocaleString('en-IN')}
                </span>
              </div>

              {/* Technical Attributes Grid */}
              <div className="grid grid-cols-2 gap-1.5 text-[9px] pt-1.5 border-t border-slate-800 font-['JetBrains_Mono']">
                <div className="flex justify-between bg-slate-900/60 px-2 py-1 rounded border border-slate-800/60">
                  <span className="text-slate-400 font-sans">CHANNEL</span>
                  <span className="text-purple-300 font-semibold">{tooltip.channel}</span>
                </div>
                <div className="flex justify-between bg-slate-900/60 px-2 py-1 rounded border border-slate-800/60">
                  <span className="text-slate-400 font-sans">HOP</span>
                  <span className="text-sky-300 font-semibold">Hop {tooltip.hop}/{tooltip.totalHops}</span>
                </div>
                {tooltip.riskScore !== null && (
                  <div className="flex justify-between bg-slate-900/60 px-2 py-1 rounded border border-slate-800/60">
                    <span className="text-slate-400 font-sans">RISK</span>
                    <span className={`font-semibold ${tooltip.riskScore >= 70 ? 'text-red-400' : 'text-slate-200'}`}>
                      {tooltip.riskScore}/100
                    </span>
                  </div>
                )}
                {tooltip.status && (
                  <div className="flex justify-between bg-slate-900/60 px-2 py-1 rounded border border-slate-800/60">
                    <span className="text-slate-400 font-sans">STATUS</span>
                    <span className="text-slate-200 font-semibold uppercase">{tooltip.status}</span>
                  </div>
                )}
                {tooltip.timestamp && (
                  <div className="col-span-2 flex justify-between bg-slate-900/60 px-2 py-1 rounded border border-slate-800/60 text-[8.5px]">
                    <span className="text-slate-500 font-sans">TIME</span>
                    <span className="text-slate-400">{new Date(tooltip.timestamp).toLocaleTimeString()}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export default React.memo(GraphCanvas);
