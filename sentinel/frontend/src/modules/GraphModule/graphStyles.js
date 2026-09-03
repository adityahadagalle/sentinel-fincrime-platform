/**
 * SENTINEL Enterprise Forensic Investigation Graph Stylesheet
 * 
 * Recreated to match the exact visual language of the reference SENTINEL graph:
 *  - Dark forensic cyber-intelligence canvas (#060B14)
 *  - High-precision geometric entities:
 *      * Victim Account: circular node, blue fill, electric blue border, small person glyph (14px)
 *      * Collector / Aggregator Hub: rounded-square, warm amber fill, bright orange border, layered stack glyph
 *      * Police / Investigation Desk: cyan hexagonal node, dashed cyan border, currency crosshair glyph
 *      * Mule Account: red threat styling with alert warning glyph
 *      * Merchant Outlet: green geometric node with storefront glyph
 *      * UPI Handle: purple diamond with lightning glyph
 *      * Cashout Terminal: amber rounded-square with ATM/card glyph
 *  - High-contrast dark backdrop labels with thin blue borders
 *  - Directional dashed red/orange threat flows with autorotated currency edge badges (e.g. ₹92,665 · IMPS)
 *  - Electric blue path tracing and subtle ambient glows
 */

const makeSvgUri = (svg) => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg.trim())}`;

// ── Precise SVG Micro-Glyphs (Small, crisp, 14px visual glyphs inside nodes) ──────
export const SVG_ICONS = {
  // 1. Victim / Feeder Account (User / Person glyph in light cyan/blue)
  victim: makeSvgUri(`
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="-5 -5 34 34" fill="none" stroke="#93C5FD" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
    </svg>
  `),
  // 2. Collector / Aggregator Hub (Layered Stack glyph in bright orange)
  collector: makeSvgUri(`
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="-5 -5 34 34" fill="none" stroke="#FB923C" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
    </svg>
  `),
  // 3. Police / Investigation Desk / Cashout (Currency / Crosshair in bright cyan)
  desk: makeSvgUri(`
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="-5 -5 34 34" fill="none" stroke="#22D3EE" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
    </svg>
  `),
  // 4. Mule / Suspect Account (Red warning shield / alert)
  mule: makeSvgUri(`
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="-5 -5 34 34" fill="none" stroke="#EF4444" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  `),
  // 5. Merchant Outlet (Storefront glyph in emerald)
  merchant: makeSvgUri(`
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="-5 -5 34 34" fill="none" stroke="#34D399" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
    </svg>
  `),
  // 6. UPI Handle (Lightning / Rail glyph in purple)
  upi: makeSvgUri(`
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="-5 -5 34 34" fill="none" stroke="#C084FC" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  `),
  // 7. Cashout Terminal (Card terminal in amber)
  cashout: makeSvgUri(`
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="-5 -5 34 34" fill="none" stroke="#FBBF24" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/>
    </svg>
  `),
  // 8. Individual / Fallback User
  individual: makeSvgUri(`
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="-5 -5 34 34" fill="none" stroke="#94A3B8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="7" r="4"/><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
    </svg>
  `)
};

// Legacy exports for compatibility
export const SVG_USER = SVG_ICONS.victim;
export const SVG_ALERT = SVG_ICONS.mule;
export const SVG_CARD = SVG_ICONS.cashout;
export const SVG_STORE = SVG_ICONS.merchant;
export const SVG_UPI = SVG_ICONS.upi;

const HEXAGON_POINTS = [-0.5,-0.866, 0.5,-0.866, 1,0, 0.5,0.866, -0.5,0.866, -1,0];

export const getNodeClassification = (node) => {
  if (node.data('is_cluster')) {
    const ct = String(node.data('cluster_type') || node.data('type') || '').toLowerCase();
    if (ct.includes('mule')) return 'MULE_CLUSTER';
    if (ct.includes('cashout') || ct.includes('exit')) return 'CASHOUT_CLUSTER';
    if (ct.includes('victim') || ct.includes('feed')) return 'VICTIM_POOL';
    return 'INTERMEDIARY_CLUSTER';
  }

  const type = String(node.data('type') || node.data('node_type') || node.data('account_type') || '').toLowerCase();
  const rawId = String(node.data('id') || node.data('accountId') || '').toUpperCase();
  const status = String(node.data('status') || '').toLowerCase();

  // Match classification
  if (type === 'victim' || type === 'feeder' || type === 'source' || rawId.includes('FEEDER') || rawId.includes('VICTIM')) return 'VICTIM';
  if (type === 'collector' || type === 'aggregator' || type === 'hub' || rawId.includes('COLLECTOR') || rawId.includes('AGGREGATOR') || rawId.includes('HUB')) return 'COLLECTOR';
  if (type === 'desk' || type === 'police' || type === 'crypto' || rawId.includes('DESK') || rawId.includes('POLICE')) return 'DESK';
  if (type === 'merchant' || rawId.includes('MERCHANT')) return 'MERCHANT';
  if (type === 'upi' || type === 'upi_handle' || rawId.includes('UPI')) return 'UPI';
  if (type === 'cashout' || type === 'atm' || type === 'destination' || rawId.includes('CASHOUT') || rawId.includes('ATM')) return 'CASHOUT';
  if (type === 'mule' || type === 'suspect' || status === 'flagged' || rawId.includes('MULE') || rawId.includes('SUSPECT')) return 'MULE';

  // Degree heuristics fallback
  const inDeg = Number(node.indegree ? node.indegree() : 0);
  const outDeg = Number(node.outdegree ? node.outdegree() : 0);
  if (inDeg > 1 && outDeg >= 1) return 'COLLECTOR';
  if (inDeg === 0 && outDeg >= 1) return 'VICTIM';
  if (inDeg >= 1 && outDeg === 0) return 'CASHOUT';

  return 'VICTIM';
};

export const isCriticalNode = (node) => {
  const cls = getNodeClassification(node);
  const status = String(node.data('status') || '').toLowerCase();
  return cls === 'MULE' || cls === 'COLLECTOR' || cls === 'MULE_CLUSTER' || status === 'flagged';
};

export const NODE_CONFIG = {
  VICTIM: {
    label: 'Victim Account',
    shape: 'ellipse',
    size: 68,
    bg: '#0A1A3C',
    innerGlow: '#1D4ED8',
    border: '#2563EB',
    borderWidth: 3.0,
    borderStyle: 'solid',
    shadowColor: '#3B82F6',
    shadowBlur: 14,
    shadowOpacity: 0.5,
    icon: SVG_ICONS.victim,
    badgeColor: '#3B82F6'
  },
  VICTIM_POOL: {
    label: 'Feeder Pool',
    shape: 'ellipse',
    size: 72,
    bg: '#0A1A3C',
    innerGlow: '#1D4ED8',
    border: '#38BDF8',
    borderWidth: 3.2,
    borderStyle: 'dashed',
    shadowColor: '#38BDF8',
    shadowBlur: 18,
    shadowOpacity: 0.65,
    icon: SVG_ICONS.victim,
    badgeColor: '#38BDF8'
  },
  COLLECTOR: {
    label: 'Collector / Aggregator',
    shape: 'round-rectangle',
    size: 74,
    bg: '#331604',
    innerGlow: '#9A3412',
    border: '#EA580C',
    borderWidth: 3.2,
    borderStyle: 'solid',
    shadowColor: '#F97316',
    shadowBlur: 20,
    shadowOpacity: 0.65,
    icon: SVG_ICONS.collector,
    badgeColor: '#F97316'
  },
  DESK: {
    label: 'Police / Investigation Desk',
    shape: 'polygon',
    polygonPoints: HEXAGON_POINTS,
    size: 68,
    bg: '#042833',
    innerGlow: '#0E7490',
    border: '#06B6D4',
    borderWidth: 2.8,
    borderStyle: 'dashed',
    shadowColor: '#06B6D4',
    shadowBlur: 16,
    shadowOpacity: 0.6,
    icon: SVG_ICONS.desk,
    badgeColor: '#06B6D4'
  },
  MULE: {
    label: 'Mule Account',
    shape: 'round-rectangle',
    size: 66,
    bg: '#330808',
    innerGlow: '#991B1B',
    border: '#DC2626',
    borderWidth: 3.0,
    borderStyle: 'solid',
    shadowColor: '#EF4444',
    shadowBlur: 20,
    shadowOpacity: 0.7,
    icon: SVG_ICONS.mule,
    badgeColor: '#EF4444'
  },
  MULE_CLUSTER: {
    label: 'Mule Cluster',
    shape: 'round-rectangle',
    size: 72,
    bg: '#3D0A0A',
    innerGlow: '#B91C1C',
    border: '#EF4444',
    borderWidth: 3.5,
    borderStyle: 'dashed',
    shadowColor: '#EF4444',
    shadowBlur: 24,
    shadowOpacity: 0.8,
    icon: SVG_ICONS.mule,
    badgeColor: '#EF4444'
  },
  MERCHANT: {
    label: 'Merchant Outlet',
    shape: 'round-rectangle',
    size: 64,
    bg: '#03261A',
    innerGlow: '#047857',
    border: '#10B981',
    borderWidth: 2.5,
    borderStyle: 'solid',
    shadowColor: '#10B981',
    shadowBlur: 14,
    shadowOpacity: 0.5,
    icon: SVG_ICONS.merchant,
    badgeColor: '#10B981'
  },
  UPI: {
    label: 'UPI Handle',
    shape: 'diamond',
    size: 64,
    bg: '#220B3D',
    innerGlow: '#6B21A8',
    border: '#9333EA',
    borderWidth: 2.5,
    borderStyle: 'solid',
    shadowColor: '#A855F7',
    shadowBlur: 14,
    shadowOpacity: 0.5,
    icon: SVG_ICONS.upi,
    badgeColor: '#A855F7'
  },
  INTERMEDIARY_CLUSTER: {
    label: 'Intermediaries Cluster',
    shape: 'diamond',
    size: 70,
    bg: '#250D42',
    innerGlow: '#7E22CE',
    border: '#C084FC',
    borderWidth: 3.2,
    borderStyle: 'dashed',
    shadowColor: '#C084FC',
    shadowBlur: 18,
    shadowOpacity: 0.65,
    icon: SVG_ICONS.upi,
    badgeColor: '#C084FC'
  },
  CASHOUT: {
    label: 'Cashout Terminal',
    shape: 'round-rectangle',
    size: 66,
    bg: '#331B03',
    innerGlow: '#B45309',
    border: '#F59E0B',
    borderWidth: 3.0,
    borderStyle: 'solid',
    shadowColor: '#F59E0B',
    shadowBlur: 16,
    shadowOpacity: 0.6,
    icon: SVG_ICONS.cashout,
    badgeColor: '#F59E0B'
  },
  CASHOUT_CLUSTER: {
    label: 'Cashout Terminals Cluster',
    shape: 'round-rectangle',
    size: 72,
    bg: '#3D1E03',
    innerGlow: '#D97706',
    border: '#FBBF24',
    borderWidth: 3.5,
    borderStyle: 'dashed',
    shadowColor: '#FBBF24',
    shadowBlur: 22,
    shadowOpacity: 0.75,
    icon: SVG_ICONS.cashout,
    badgeColor: '#FBBF24'
  }
};

export const getNodeConfig = (node) => {
  const cls = getNodeClassification(node);
  return NODE_CONFIG[cls] || NODE_CONFIG.VICTIM;
};

// ── Node Label Formatting ──────────────────────────────────────────────────
export const getNodeLabel = (node) => {
  if (node.data('is_cluster')) {
    return String(node.data('label') || node.data('displayLabel') || 'CLUSTER');
  }
  const raw = String(node.data('displayLabel') || node.data('accountId') || node.data('id') || '');
  const status = (node.data('status') || '').toLowerCase();
  const statusGlyph = status === 'frozen' ? ' 🔒' : status === 'withdrawn' ? ' ✕' : '';
  
  if (raw.length > 17) {
    return `${raw.slice(0, 9)}...${raw.slice(-4)}${statusGlyph}`;
  }
  return `${raw}${statusGlyph}`;
};

// ── Edge Label Formatting (₹ Amount · Channel) ─────────────────────────────
export const getEdgeLabel = (edge) => {
  const customLabel = edge.data('label');
  if (customLabel && customLabel.includes('·')) return customLabel;
  const amt = Number(edge.data('amount') || 0);
  const formatted = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(amt);
  const channel = edge.data('channel') || 'UPI';
  const cleanChannel = channel.replace(/_/g, ' ').toUpperCase();
  return `₹${formatted} · ${cleanChannel}`;
};

// ── Edge Color by Risk & Flow Type ─────────────────────────────────────────
export const getEdgeColor = (edge) => {
  if (edge.data('is_suspicious') || edge.data('suspicious') || edge.hasClass('suspicious-edge')) return '#EF4444';
  const amt = Number(edge.data('amount') || 0);
  if (amt >= 80000) return '#EF4444'; // Suspicious threshold
  if (amt >= 40000) return '#F97316'; // High value flow
  return '#2563EB';                  // Electric blue normal flow
};

export const graphStyles = [
  /* ── Master Node: 3D Radial Sphere + Scaled SVG Micro-Glyph ─────────── */
  {
    selector: 'node',
    style: {
      'label': (n) => getNodeLabel(n),
      'shape': (n) => {
        const cfg = getNodeConfig(n);
        if (cfg.shape === 'polygon') return 'polygon';
        return cfg.shape || 'ellipse';
      },
      'shape-polygon-points': (n) => {
        const cfg = getNodeConfig(n);
        return cfg.polygonPoints || HEXAGON_POINTS;
      },

      // 3D Spherical Radial Depth Fill
      'background-fill': 'radial-gradient',
      'background-gradient-stop-colors': (n) => {
        const c = getNodeConfig(n);
        return `${c.innerGlow} ${c.bg}`;
      },
      'background-gradient-stop-positions': '0% 100%',
      'background-color': (n) => getNodeConfig(n).bg,
      'border-color': (n) => {
        if ((n.data('status') || '').toLowerCase() === 'frozen') return '#64748B';
        return getNodeConfig(n).border;
      },
      'border-width': (n) => {
        if ((n.data('status') || '').toLowerCase() === 'frozen') return 3.5;
        return getNodeConfig(n).borderWidth;
      },
      'border-style': (n) => getNodeConfig(n).borderStyle || 'solid',
      'width': (n) => getNodeConfig(n).size,
      'height': (n) => getNodeConfig(n).size,

      // Scaled SVG Micro-Glyph (small, crisp 14px visual glyph inside node)
      'background-image': (n) => getNodeConfig(n).icon || SVG_ICONS.victim,
      'background-fit': 'none',
      'background-width': '14px',
      'background-height': '14px',
      'background-position-x': '50%',
      'background-position-y': '50%',
      'background-image-opacity': 0.95,

      // Ambient Threat & Entity Glow
      'shadow-blur': (n) => getNodeConfig(n).shadowBlur || 14,
      'shadow-color': (n) => getNodeConfig(n).shadowColor || '#2563EB',
      'shadow-opacity': (n) => getNodeConfig(n).shadowOpacity || 0.5,
      'shadow-offset-x': 0,
      'shadow-offset-y': 0,

      // Node Identifier Pill Label
      'color': '#F1F5F9',
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 10,
      'font-size': 9.5,
      'font-family': 'JetBrains Mono, monospace',
      'font-weight': 700,
      'text-background-color': '#060B14',
      'text-background-opacity': 0.95,
      'text-background-padding': '4px',
      'text-background-shape': 'round-rectangle',
      'text-border-color': '#1E2D4A',
      'text-border-width': 1.2,
      'text-border-opacity': 1.0,
      'text-max-width': '140px',
      'text-wrap': 'ellipsis',
      'overlay-opacity': 0,
      'transition-property': 'background-color, border-color, border-width, opacity, shadow-blur, shadow-opacity',
      'transition-duration': '0.2s'
    }
  },

  /* ── Master Edge: Directional Dashed Threat Flow with Currency Badge ── */
  {
    selector: 'edge',
    style: {
      'label': (e) => getEdgeLabel(e),
      'width': (e) => e.data('is_primary_path') ? 3.4 : 2.2,
      'line-style': 'dashed',
      'line-dash-pattern': [8, 5],
      'line-color': (e) => getEdgeColor(e),
      'target-arrow-color': (e) => getEdgeColor(e),
      'target-arrow-shape': 'triangle',
      'arrow-scale': (e) => e.data('is_primary_path') ? 1.35 : 1.15,
      'curve-style': 'bezier',
      'control-point-step-size': 40,

      // Edge Currency Badge Label
      'font-size': 9,
      'font-family': 'JetBrains Mono, monospace',
      'font-weight': 700,
      'color': (e) => {
        const isSusp = e.data('is_suspicious') || e.data('suspicious') || e.hasClass('suspicious-edge');
        return isSusp ? '#FCA5A5' : '#93C5FD';
      },
      'text-rotation': 'autorotate',
      'text-margin-y': -11,
      'text-background-color': '#080608',
      'text-background-opacity': 0.95,
      'text-background-padding': '3.5px',
      'text-background-shape': 'round-rectangle',
      'text-border-color': (e) => getEdgeColor(e),
      'text-border-width': 1.2,
      'text-border-opacity': 0.95,
      'opacity': (e) => e.data('is_primary_path') === false ? 0.7 : 0.95,
      'transition-property': 'line-color, target-arrow-color, opacity, width, shadow-blur',
      'transition-duration': '0.25s'
    }
  },

  /* ── Selected Path Highlighting ────────────────────────────────────────── */
  {
    selector: 'edge.highlighted, edge.path-highlight, edge.traced-edge',
    style: {
      'width': 4.0,
      'line-style': 'solid',
      'line-color': '#38BDF8',
      'target-arrow-color': '#38BDF8',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 1.4,
      'opacity': 1.0,
      'z-index': 50,
      'shadow-blur': 18,
      'shadow-color': '#38BDF8',
      'shadow-opacity': 0.9,
      'color': '#E0F2FE',
      'text-background-color': '#031428',
      'text-border-color': '#38BDF8',
      'text-border-width': 1.5
    }
  },
  {
    selector: 'node.highlighted, node.path-highlight, node.hovered-focus, node:selected',
    style: {
      'border-width': 4.0,
      'border-color': '#38BDF8',
      'shadow-blur': 26,
      'shadow-color': '#38BDF8',
      'shadow-opacity': 0.95,
      'z-index': 40
    }
  },
  {
    selector: 'edge:selected',
    style: {
      'width': 4.0,
      'line-color': '#38BDF8',
      'target-arrow-color': '#38BDF8',
      'z-index': 50
    }
  },

  /* ── Suspicious Flow Edge ──────────────────────────────────────────────── */
  {
    selector: 'edge.suspicious-edge',
    style: {
      'line-color': '#EF4444',
      'target-arrow-color': '#EF4444',
      'text-border-color': '#EF4444',
      'color': '#FCA5A5'
    }
  },
  {
    selector: 'edge.new-transaction-pulse',
    style: {
      'width': 4.5,
      'line-color': '#EF4444',
      'target-arrow-color': '#EF4444',
      'opacity': 1,
      'z-index': 45
    }
  },

  /* ── Dimmed Unselected Graph Elements ─────────────────────────────────── */
  {
    selector: 'node.dimmed',
    style: {
      'opacity': 0.12,
      'shadow-opacity': 0,
      'background-image-opacity': 0.1
    }
  },
  {
    selector: 'edge.dimmed',
    style: {
      'opacity': 0.08,
      'shadow-opacity': 0
    }
  }
];
