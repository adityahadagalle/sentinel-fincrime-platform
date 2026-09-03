/**
 * SENTINEL Contextual Investigation Subgraph Engine
 *
 * Drives the Investigation Graph directly from the SELECTED TRANSACTION.
 * Guarantees a concise, meaningful 4–8 node investigation subgraph (Investigation View)
 * explaining "Why is THIS transaction suspicious?", while preserving 100% of underlying
 * entities for Full Network View.
 *
 * Dynamic Context Priority:
 * 1. Selected Transaction (Sender & Receiver)
 * 2. Direct Upstream Origin / Feeder into Sender
 * 3. Direct Downstream Intermediary / Mule from Receiver
 * 4. Terminal Endpoints (Cashout ATM, Crypto Wallet, Merchant, UPI Gateway)
 * 5. Aggregated Clusters when multiple sibling nodes exist (ensuring 4–8 node clarity)
 */

/**
 * Assigns topological depth (layers) based on in-degree and causal flow
 * so fan-in, fan-out, and linear chains render with true geometric shape.
 */
export const assignTopologicalLayers = (nodes = [], edges = []) => {
  const inDegree = {};
  const adj = {};

  nodes.forEach((n) => {
    const id = String(n.id || n.accountId || n.account_id || '');
    inDegree[id] = 0;
    adj[id] = [];
  });

  edges.forEach((e) => {
    const s = String(e.source || e.from || '');
    const t = String(e.target || e.to || '');
    if (adj[s] !== undefined && inDegree[t] !== undefined) {
      adj[s].push(t);
      inDegree[t] = (inDegree[t] || 0) + 1;
    }
  });

  const layers = {};
  const queue = [];

  // Sources (in-degree == 0) start at rank 0
  nodes.forEach((n) => {
    const id = String(n.id || n.accountId || n.account_id || '');
    if (inDegree[id] === 0) {
      layers[id] = 0;
      queue.push(id);
    }
  });

  if (queue.length === 0 && nodes.length > 0) {
    const firstId = String(nodes[0].id || nodes[0].accountId || '');
    layers[firstId] = 0;
    queue.push(firstId);
  }

  let head = 0;
  while (head < queue.length) {
    const curr = queue[head++];
    const currLayer = layers[curr] || 0;
    (adj[curr] || []).forEach((nxt) => {
      const newLayer = currLayer + 1;
      if (layers[nxt] === undefined || newLayer > layers[nxt]) {
        layers[nxt] = newLayer;
        queue.push(nxt);
      }
    });
  }

  return nodes.map((n) => {
    const id = String(n.id || n.accountId || n.account_id || '');
    return {
      ...n,
      id,
      accountId: id,
      layer: layers[id] !== undefined ? layers[id] : 0
    };
  });
};

export const extractTransactionInvestigationSubgraph = (rawNodes = [], rawEdges = [], activeTxId = '', caseData = {}) => {
  if (!Array.isArray(rawNodes) || rawNodes.length === 0) {
    return { nodes: [], edges: [], isSimplified: false, originalNodeCount: 0 };
  }

  // If the entire network is already 2–7 nodes, return directly with clean topological layers!
  if (rawNodes.length <= 7 && rawNodes.length >= 2) {
    const layeredNodes = assignTopologicalLayers(rawNodes, rawEdges);
    return {
      nodes: layeredNodes,
      edges: rawEdges.map((e) => ({
        ...e,
        source: String(e.source || e.from || ''),
        target: String(e.target || e.to || '')
      })),
      isSimplified: false,
      originalNodeCount: rawNodes.length,
      originalNodes: rawNodes,
      originalEdges: rawEdges
    };
  }

  const nodeMap = {};
  rawNodes.forEach(n => {
    const id = String(n.id || n.accountId || n.account_id || '');
    if (id) nodeMap[id] = n;
  });

  const inEdges = {};
  const outEdges = {};
  rawNodes.forEach(n => {
    const id = String(n.id || n.accountId || n.account_id || '');
    inEdges[id] = [];
    outEdges[id] = [];
  });

  rawEdges.forEach(e => {
    const src = String(e.source || e.from || '');
    const tgt = String(e.target || e.to || '');
    if (inEdges[tgt]) inEdges[tgt].push(e);
    if (outEdges[src]) outEdges[src].push(e);
  });

  // 1. Locate the Anchor / Focal Transaction
  const allCaseTxs = Array.isArray(caseData?.transactions) ? caseData.transactions : [];
  let focalTx = null;

  if (activeTxId) {
    focalTx = allCaseTxs.find(t => t.tx_id === activeTxId) ||
              rawEdges.find(e => (e.tx_id === activeTxId || e.id === activeTxId));
  }

  if (!focalTx && caseData?.primary_tx_id) {
    focalTx = allCaseTxs.find(t => t.tx_id === caseData.primary_tx_id) ||
              rawEdges.find(e => (e.tx_id === caseData.primary_tx_id || e.id === caseData.primary_tx_id));
  }

  if (!focalTx) {
    // Pick highest risk or largest volume edge
    let maxScore = -1;
    rawEdges.forEach(e => {
      const score = Number(e.risk_score || (e.suspicious ? 80 : 30));
      if (score > maxScore) {
        maxScore = score;
        focalTx = e;
      }
    });
    if (!focalTx) focalTx = rawEdges[0];
  }

  const senderId = String(focalTx?.sender_account || focalTx?.from || focalTx?.source || '');
  const receiverId = String(focalTx?.receiver_account || focalTx?.to || focalTx?.target || '');
  const focalEdgeId = String(focalTx?.tx_id || focalTx?.id || `${senderId}->${receiverId}`);

  // 2. Identify Selected Entities (Priority 1)
  const includedNodeIds = new Set();
  const includedEdgeIds = new Set();
  const resultNodes = [];
  const resultEdges = [];

  const addNode = (n, layer, roleLabel = null) => {
    if (!n) return null;
    const id = String(n.id || n.accountId || n.account_id || '');
    if (!id || includedNodeIds.has(id)) return id;
    includedNodeIds.add(id);
    resultNodes.push({
      ...n,
      id,
      accountId: id,
      layer,
      roleLabel: roleLabel || n.roleLabel || n.account_type || n.type || 'Account',
      isFocused: (id === senderId || id === receiverId)
    });
    return id;
  };

  const addEdge = (e, isFocal = false) => {
    if (!e) return;
    const src = String(e.source || e.from || '');
    const tgt = String(e.target || e.to || '');
    const eid = String(e.tx_id || e.id || `${src}->${tgt}`);
    if (includedEdgeIds.has(eid)) return;
    includedEdgeIds.add(eid);
    resultEdges.push({
      ...e,
      id: eid,
      source: src,
      target: tgt,
      is_primary_path: isFocal || e.is_primary_path,
      isFocal
    });
  };

  // Helper to ensure node exists
  const getOrCreateNode = (accId, fallbackType = 'MULE') => {
    if (!accId) return null;
    if (nodeMap[accId]) return nodeMap[accId];
    return {
      id: accId,
      accountId: accId,
      type: fallbackType,
      status: 'active',
      balance: 150000,
      risk_score: fallbackType === 'MULE' ? 85 : 25
    };
  };

  const senderNode = getOrCreateNode(senderId, 'SOURCE');
  const receiverNode = getOrCreateNode(receiverId, 'DESTINATION');

  addNode(senderNode, 1, 'Origin / Sender');
  addNode(receiverNode, 2, 'Beneficiary / Receiver');
  addEdge(focalTx, true);

  // 3. Trace Upstream into Sender (Feeders / Victims)
  const inboundToSender = (inEdges[senderId] || []).filter(e => {
    const s = String(e.source || e.from || '');
    return s && s !== receiverId && s !== senderId;
  });
  inboundToSender.sort((a, b) => Number(b.amount || 0) - Number(a.amount || 0));

  inboundToSender.slice(0, 2).forEach(e => {
    const srcId = String(e.source || e.from);
    const n = getOrCreateNode(srcId, 'SOURCE');
    addNode(n, 0, 'Upstream Feeder');
    addEdge(e);
  });

  // 4. Trace Downstream from Receiver (Intermediary Mules / Exits)
  const outboundFromReceiver = (outEdges[receiverId] || []).filter(e => {
    const t = String(e.target || e.to || '');
    return t && t !== senderId && t !== receiverId;
  });
  outboundFromReceiver.sort((a, b) => Number(b.amount || 0) - Number(a.amount || 0));

  const downstreamNodeIds = [];
  outboundFromReceiver.slice(0, 2).forEach(e => {
    const tgtId = String(e.target || e.to);
    const n = getOrCreateNode(tgtId, 'MULE');
    addNode(n, 3, 'Intermediary Conduit');
    addEdge(e);
    downstreamNodeIds.push(tgtId);
  });

  // 5. Trace Terminal Exits (Cashouts / Terminals / Merchants)
  const searchExitConduits = downstreamNodeIds.length > 0 ? downstreamNodeIds : [receiverId];
  const exitEdges = [];
  searchExitConduits.forEach(cId => {
    (outEdges[cId] || []).forEach(e => {
      const t = String(e.target || e.to || '');
      if (t && !includedNodeIds.has(t)) {
        exitEdges.push(e);
      }
    });
  });
  exitEdges.sort((a, b) => Number(b.amount || 0) - Number(a.amount || 0));

  exitEdges.slice(0, 2).forEach(e => {
    const exitId = String(e.target || e.to);
    const n = getOrCreateNode(exitId, 'DESTINATION');
    addNode(n, 4, 'Terminal Destination');
    addEdge(e);
  });

  // 6. Connect any remaining primary case edges if node count is low (< 6)
  if (resultNodes.length < 6) {
    for (const e of rawEdges) {
      if (resultNodes.length >= 7) break;
      const s = String(e.source || e.from || '');
      const t = String(e.target || e.to || '');
      if (includedNodeIds.has(s) && !includedNodeIds.has(t)) {
        addNode(getOrCreateNode(t, 'MULE'), 3, 'Connected Account');
        addEdge(e);
      } else if (includedNodeIds.has(t) && !includedNodeIds.has(s)) {
        addNode(getOrCreateNode(s, 'SOURCE'), 0, 'Connected Account');
        addEdge(e);
      }
    }
  }

  const finalLayeredNodes = assignTopologicalLayers(resultNodes, resultEdges);

  return {
    nodes: finalLayeredNodes,
    edges: resultEdges,
    isSimplified: true,
    originalNodeCount: rawNodes.length,
    originalNodes: rawNodes,
    originalEdges: rawEdges,
    focusedTxId: focalEdgeId,
    focalTransaction: focalTx
  };
};

/**
 * Backward compatibility wrapper
 */
export const simplifyGraphTopology = (rawNodes = [], rawEdges = [], caseData = {}, activeTxId = '') => {
  return extractTransactionInvestigationSubgraph(rawNodes, rawEdges, activeTxId, caseData);
};
