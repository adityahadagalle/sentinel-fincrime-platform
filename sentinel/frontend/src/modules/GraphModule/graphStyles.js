// ── SENTINEL FINANCIAL-CRIME INVESTIGATION DESIGN SYSTEM ─────────────────────────
// Clean, authoritative, enterprise styling for high-precision fraud investigation graphs.

export const STATUS_STYLES = {
  active:    { bg: '#0369A1', border: '#38BDF8', icon: '●' },
  flagged:   { bg: '#B45309', border: '#F59E0B', icon: '⚠' },
  frozen:    { bg: '#1E293B', border: '#64748B', icon: '🔒' },
  withdrawn: { bg: '#881337', border: '#F43F5E', icon: '✕' }
};

export const TYPE_STYLES = {
  SOURCE:       { bg: '#0C2340', border: '#38BDF8', badge: 'ORIGIN',   shape: 'ellipse' },
  MULE:         { bg: '#2A0808', border: '#F87171', badge: 'MULE',     shape: 'octagon' },
  INTERMEDIARY: { bg: '#221808', border: '#FBBF24', badge: 'HUB',      shape: 'round-rectangle' },
  DESTINATION:  { bg: '#06251A', border: '#34D399', badge: 'OUTLET',   shape: 'round-rectangle' },
  SUSPECT:      { bg: '#2A0808', border: '#FB7185', badge: 'SUSPECT',  shape: 'octagon' },
  VICTIM:       { bg: '#0C2340', border: '#38BDF8', badge: 'VICTIM',   shape: 'ellipse' }
};

export const NODE_SHAPE_MAP = {
  victim:     'ellipse',
  mule:       'octagon',
  merchant:   'round-rectangle',
  UPI:        'diamond',
  cashout:    'pentagon',
  crypto:     'hexagon',
  collector:  'round-rectangle',
  individual: 'ellipse'
};

export const NODE_BG_MAP = {
  victim:     '#0C2340',
  mule:       '#2A0808',
  merchant:   '#06251A',
  UPI:        '#1E1035',
  cashout:    '#2E0B18',
  crypto:     '#1E1035',
  collector:  '#221808',
  individual: '#0B1E36'
};

export const NODE_BORDER_MAP = {
  victim:     '#38BDF8',
  mule:       '#F87171',
  merchant:   '#34D399',
  UPI:        '#C084FC',
  cashout:    '#FB7185',
  crypto:     '#A78BFA',
  collector:  '#FBBF24',
  individual: '#38BDF8'
};

export const graphStyles = [
  // ── BASE NODE DEFINITION ──────────────────────────────────────────────────
  {
    selector: 'node',
    style: {
      'shape': (node) => {
        const ntype = node.data('node_type');
        if (ntype && NODE_SHAPE_MAP[ntype]) return NODE_SHAPE_MAP[ntype];
        const atype = node.data('account_type');
        if (atype && TYPE_STYLES[atype]) return TYPE_STYLES[atype].shape;
        return 'ellipse';
      },
      'label': (node) => {
        const id = node.data('displayLabel') || node.data('accountId') || node.data('id') || '';
        const ntype = (node.data('node_type') || node.data('account_type') || 'ACCT').toUpperCase();
        const shortId = String(id).length > 12 ? String(id).slice(0, 10) + '…' : String(id);
        return `${shortId}\n${ntype}`;
      },
      'background-color': (node) => {
        const status = node.data('status');
        if (status === 'frozen') return '#0F172A';
        const ntype = node.data('node_type');
        if (ntype && NODE_BG_MAP[ntype]) return NODE_BG_MAP[ntype];
        const atype = node.data('account_type');
        if (atype && TYPE_STYLES[atype]) return TYPE_STYLES[atype].bg;
        return '#0A1324';
      },
      'border-width': 1.5,
      'border-color': (node) => {
        const status = node.data('status');
        if (status === 'frozen') return '#64748B';
        if (status === 'flagged') return '#F59E0B';
        const ntype = node.data('node_type');
        if (ntype && NODE_BORDER_MAP[ntype]) return NODE_BORDER_MAP[ntype];
        const atype = node.data('account_type');
        if (atype && TYPE_STYLES[atype]) return TYPE_STYLES[atype].border;
        return '#38BDF8';
      },
      'border-style': 'solid',
      'background-opacity': 0.98,
      'color': '#F1F5F9',
      'text-valign': 'center',
      'text-halign': 'center',
      'text-wrap': 'wrap',
      'text-max-width': 62,
      'font-size': 8,
      'font-family': 'JetBrains Mono, monospace',
      'font-weight': '600',
      'width': 70,
      'height': 70,
      'text-outline-width': 1.5,
      'text-outline-color': '#020617',
      'overlay-opacity': 0,
      'transition-property': 'background-color, border-color, border-width, width, height, opacity',
      'transition-duration': '0.2s'
    }
  },

  // ── BASE EDGE DEFINITION ──────────────────────────────────────────────────
  {
    selector: 'edge',
    style: {
      'label': (edge) => {
        const amt = Number(edge.data('amount') || 0);
        const formatted = new Intl.NumberFormat('en-IN').format(Math.round(amt));
        const ch = edge.data('channel') || 'UPI';
        const hop = edge.data('hop_number') || 1;
        const totalHops = edge.data('total_hops');
        const hopStr = totalHops > 1 ? ` · H${hop}/${totalHops}` : (hop > 1 ? ` · H${hop}` : '');
        return `₹${formatted} · ${ch}${hopStr}`;
      },
      'width': (edge) => edge.data('suspicious') ? 2.25 : 1.75,
      'line-color': (edge) => edge.data('suspicious') ? '#EF4444' : '#38BDF8',
      'target-arrow-color': (edge) => edge.data('suspicious') ? '#EF4444' : '#38BDF8',
      'line-style': (edge) => edge.data('suspicious') ? 'dashed' : 'solid',
      'line-dash-pattern': [6, 4],
      'target-arrow-shape': 'triangle',
      'arrow-scale': 1.15,
      'curve-style': 'bezier',
      'control-point-step-size': 40,
      'font-size': 8,
      'font-family': 'JetBrains Mono, monospace',
      'font-weight': '600',
      'color': '#E2E8F0',
      'text-rotation': 'autorotate',
      'text-margin-y': -9,
      'text-background-color': '#060B15',
      'text-background-opacity': 0.96,
      'text-background-padding': '3px 5px',
      'text-border-color': '#1E293B',
      'text-border-width': 1,
      'text-border-opacity': 0.9,
      'opacity': 0.88,
      'transition-property': 'line-color, target-arrow-color, width, opacity, text-border-color, text-background-color',
      'transition-duration': '0.2s'
    }
  },

  // ── PRECISION MONEY FLOW HOVER CLASSES ────────────────────────────────────
  {
    // The node directly inspected by cursor
    selector: 'node.node-hovered',
    style: {
      'border-width': 2.5,
      'border-color': '#FFFFFF',
      'width': 74,
      'height': 74,
      'background-opacity': 1,
      'z-index': 100
    }
  },
  {
    // Immediate Incoming Edge(s): Money entering the hovered entity
    selector: 'edge.flow-incoming',
    style: {
      'width': 2.75,
      'line-color': '#10B981',
      'target-arrow-color': '#10B981',
      'opacity': 1,
      'z-index': 85,
      'text-background-color': '#041A13',
      'text-border-color': '#10B981',
      'text-border-width': 1,
      'color': '#A7F3D0',
      'font-weight': '600',
      'arrow-scale': 1.25
    }
  },
  {
    // Immediate Outgoing Edge(s): Money leaving the hovered entity
    selector: 'edge.flow-outgoing',
    style: {
      'width': 2.75,
      'line-color': '#F59E0B',
      'target-arrow-color': '#F59E0B',
      'opacity': 1,
      'z-index': 85,
      'text-background-color': '#1F1405',
      'text-border-color': '#F59E0B',
      'text-border-width': 1,
      'color': '#FDE68A',
      'font-weight': '600',
      'arrow-scale': 1.25
    }
  },
  {
    // Upstream Source node connected via an incoming flow
    selector: 'node.node-flow-source',
    style: {
      'border-width': 2.5,
      'border-color': '#10B981',
      'opacity': 1,
      'z-index': 80
    }
  },
  {
    // Downstream Target node connected via an outgoing flow
    selector: 'node.node-flow-target',
    style: {
      'border-width': 2.5,
      'border-color': '#F59E0B',
      'opacity': 1,
      'z-index': 80
    }
  },
  {
    // Directly hovered transaction edge
    selector: 'edge.edge-hovered',
    style: {
      'width': 3,
      'line-color': '#38BDF8',
      'target-arrow-color': '#38BDF8',
      'opacity': 1,
      'z-index': 95,
      'text-background-color': '#071527',
      'text-border-color': '#38BDF8',
      'text-border-width': 1,
      'color': '#FFFFFF',
      'font-weight': '600',
      'arrow-scale': 1.3
    }
  },

  // ── SELECTION & TRACING STATES ────────────────────────────────────────────
  {
    // Selected node - subtle blue focus
    selector: 'node:selected',
    style: {
      'border-width': 2.5,
      'border-color': '#38BDF8',
      'width': 74,
      'height': 74,
      'z-index': 90
    }
  },
  {
    // Selected edge
    selector: 'edge:selected',
    style: {
      'width': 3,
      'line-color': '#38BDF8',
      'target-arrow-color': '#38BDF8',
      'z-index': 90
    }
  },
  {
    selector: 'node.path-highlight',
    style: {
      'border-width': 2.5,
      'border-color': '#38BDF8',
      'background-opacity': 1,
      'z-index': 70
    }
  },
  {
    selector: 'edge.path-highlight',
    style: {
      'width': 3,
      'line-color': '#38BDF8',
      'target-arrow-color': '#38BDF8',
      'opacity': 1,
      'z-index': 70,
      'line-style': 'solid',
      'text-background-color': '#071527',
      'text-border-color': '#38BDF8',
      'text-border-width': 1
    }
  },
  {
    selector: 'edge.new-transaction-pulse',
    style: {
      'width': 3.5,
      'line-color': '#EF4444',
      'target-arrow-color': '#EF4444',
      'opacity': 1,
      'z-index': 100,
      'text-background-color': '#3B0A12',
      'text-border-color': '#EF4444',
      'text-border-width': 1
    }
  },
  {
    // Dimmed state for unrelated elements during focus/hover
    selector: '.dimmed',
    style: {
      'opacity': 0.18
    }
  },

  // ── REVEAL ANIMATION CLASSES ─────────────────────────────────────────────
  {
    // Elements hidden by the progressive reveal animation.
    selector: '.reveal-hidden',
    style: {
      'opacity': 0,
      'events': 'no'
    }
  },
  {
    // Applied to a destination node the moment it is revealed / receives money flow
    selector: 'node.node-arriving',
    style: {
      'border-width': 3,
      'border-color': '#38BDF8',
      'width': 74,
      'height': 74,
      'background-opacity': 1,
      'z-index': 100,
      'transition-property': 'width, height, border-width, border-color, background-opacity',
      'transition-duration': '0.3s'
    }
  }
];
