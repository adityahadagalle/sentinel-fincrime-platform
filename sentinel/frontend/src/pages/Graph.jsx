import { useMemo, useCallback, useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useWebSocket } from '../hooks/useWebSocket';
import GraphModule from '../modules/GraphModule';
import ErrorBoundary from '../components/ErrorBoundary';

const Graph = () => {
  const { caseId } = useParams();
  const [searchParams] = useSearchParams();
  const txFromUrl = searchParams.get('tx') || searchParams.get('txId') || '';
  const { cases, transactions, actions, connectionStatus, lastTxEvent } = useWebSocket();
  const [fetchedCase, setFetchedCase] = useState(null);
  const [fetchedGraph, setFetchedGraph] = useState(null);

  // 1. Fetch Case Data
  useEffect(() => {
    setFetchedCase(null);
    if (!caseId) return;
    const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
    let isMounted = true;

    fetch(`${API_BASE}/cases/${caseId}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (isMounted && data && data.case_id) {
          setFetchedCase(data);
        }
      })
      .catch(() => {});

    return () => { isMounted = false; };
  }, [caseId]);

  // 2. Fetch Transaction-Specific Graph if txFromUrl is present
  useEffect(() => {
    setFetchedGraph(null);
    const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
    let isMounted = true;

    if (txFromUrl) {
      fetch(`${API_BASE}/transactions/${txFromUrl}/graph`)
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (isMounted && data && Array.isArray(data.nodes) && data.nodes.length > 0) {
            setFetchedGraph(data);
          } else if (caseId) {
            return fetch(`${API_BASE}/cases/${caseId}/graph?tx_id=${txFromUrl}`)
              .then((r) => (r.ok ? r.json() : null))
              .then((caseGraph) => {
                if (isMounted && caseGraph) setFetchedGraph(caseGraph);
              });
          }
        })
        .catch(() => {});
    } else if (caseId) {
      fetch(`${API_BASE}/cases/${caseId}/graph`)
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (isMounted && data) setFetchedGraph(data);
        })
        .catch(() => {});
    }

    return () => { isMounted = false; };
  }, [caseId, txFromUrl]);

  const selectedCase = useMemo(
    () => cases.find((c) => c.case_id === caseId) || null,
    [caseId, cases]
  );

  const matchedTx = useMemo(
    () => (txFromUrl ? (transactions || []).find((t) => t.tx_id === txFromUrl) : null),
    [txFromUrl, transactions]
  );

  // Build the activeCase payload strictly derived from real data
  const activeCase = useMemo(() => {
    const base = fetchedCase || selectedCase;

    // If a specific transaction was requested
    if (txFromUrl) {
      // 1. If backend returned transaction-anchored graph, prioritize it
      if (fetchedGraph?.nodes && fetchedGraph.nodes.length > 0) {
        return {
          case_id: caseId || matchedTx?.case_id || fetchedGraph.case_id || `CASE-${txFromUrl.slice(-8)}`,
          primary_tx_id: txFromUrl,
          status: (matchedTx?.risk_score || 0) >= 70 ? 'HIGH_RISK' : 'NEW',
          risk_level: matchedTx?.risk_score || 50,
          total_fraud_amount: matchedTx?.amount || 0,
          nodes: fetchedGraph.nodes,
          edges: fetchedGraph.edges,
          topology_type: fetchedGraph.topology_type || 'DIRECT_TRANSFER',
          transactions: matchedTx ? [matchedTx] : []
        };
      }

      // 2. Otherwise derive from live related transactions in memory if matchedTx is available
      if (matchedTx) {
      const relatedTxs = (transactions || []).filter(t => 
        t && (
          t.tx_id === matchedTx.tx_id ||
          (t.case_id && t.case_id === matchedTx.case_id) ||
          (t.chain_id && t.chain_id === matchedTx.chain_id) ||
          t.receiver_account === matchedTx.sender_account ||
          t.sender_account === matchedTx.receiver_account
        )
      );

      const nodeMap = {};
      const edgeList = [];

      relatedTxs.forEach((t, idx) => {
        const s = t.sender_account;
        const r = t.receiver_account;
        if (s && !nodeMap[s]) {
          nodeMap[s] = {
            id: s,
            accountId: s,
            account_id: s,
            account_type: s.startsWith('ACC-USR') ? 'SOURCE' : 'MULE',
            type: s.startsWith('ACC-USR') ? 'victim' : 'mule',
            status: 'active',
            balance: 125000,
            risk_score: 20
          };
        }
        if (r && !nodeMap[r]) {
          nodeMap[r] = {
            id: r,
            accountId: r,
            account_id: r,
            account_type: r.startsWith('ACC-MERCH') ? 'DESTINATION' : 'MULE',
            type: r.startsWith('ACC-MERCH') ? 'merchant' : 'mule',
            status: t.risk_score >= 70 ? 'flagged' : 'active',
            balance: t.amount,
            risk_score: t.risk_score || 50
          };
        }
        edgeList.push({
          id: t.tx_id || `e-${idx}`,
          tx_id: t.tx_id,
          source: s,
          target: r,
          from: s,
          to: r,
          amount: t.amount,
          channel: t.channel || 'UPI',
          hop_number: t.hop_number || (idx + 1),
          total_hops: t.total_hops || relatedTxs.length,
          is_suspicious: (t.risk_score || 0) >= 60,
          timestamp: t.timestamp || ''
        });
      });

      return {
        case_id: caseId || matchedTx.case_id || `CASE-${matchedTx.tx_id.slice(-8)}`,
        primary_tx_id: matchedTx.tx_id,
        status: matchedTx.risk_score >= 70 ? 'HIGH_RISK' : 'NEW',
        risk_level: matchedTx.risk_score,
        total_fraud_amount: matchedTx.amount,
        transactions: relatedTxs,
        nodes: Object.values(nodeMap),
        edges: edgeList,
        topology_type: edgeList.length === 1 ? 'DIRECT_TRANSFER' : 'LINEAR_CHAIN'
      };
      }
    }

    if (base) {
      return {
        ...base,
        nodes: fetchedGraph?.nodes && fetchedGraph.nodes.length > 0 ? fetchedGraph.nodes : (base.nodes || []),
        edges: fetchedGraph?.edges && fetchedGraph.edges.length > 0 ? fetchedGraph.edges : (base.edges || []),
        topology_type: fetchedGraph?.topology_type || base.topology_type,
        primary_tx_id: txFromUrl || base.primary_tx_id
      };
    }

    return null;
  }, [fetchedCase, selectedCase, fetchedGraph, matchedTx, transactions, caseId, txFromUrl]);

  const handleAction = useCallback(async (type, payload) => {
    const endpointByType = {
      freeze: '/action/freeze',
      flag: '/action/flag',
      alert: '/action/alert',
      monitor: '/action/monitor',
      close: '/action/close',
      close_fp: '/action/close_fp'
    };
    const endpoint = endpointByType[type];
    if (!endpoint) return;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    const actionPayload = {
      case_id: caseId,
      account_id: payload?.accountId || payload?.target || 'GLOBAL',
      ...payload
    };

    let res;
    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(actionPayload),
        signal: controller.signal
      });
    } finally {
      clearTimeout(timeoutId);
    }
    if (!res.ok) {
      throw new Error(`Action failed with status ${res.status}`);
    }
  }, [caseId]);

  if (!activeCase && cases.length === 0 && connectionStatus === 'LIVE') {
    return (
      <div className="flex items-center justify-center h-full p-8 text-slate-400 font-mono text-xs">
        Loading transaction graph...
      </div>
    );
  }

  if (connectionStatus === 'OFFLINE' && !activeCase) {
    return (
      <div className="flex items-center justify-center h-full p-8 text-rose-400 font-mono text-xs">
        Graph unavailable while offline.
      </div>
    );
  }

  if (!activeCase) {
    return (
      <div className="flex items-center justify-center h-full p-8 text-slate-400 font-mono text-xs">
        No case or transaction selected.
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="w-full h-full flex flex-col overflow-hidden">
        <GraphModule
          key={`${activeCase.case_id || caseId}-${txFromUrl || activeCase.primary_tx_id || 'default'}`}
          caseData={activeCase}
          selectedTxId={txFromUrl}
          actions={actions}
          onAction={handleAction}
          connectionStatus={connectionStatus}
          newTransactionEvent={lastTxEvent}
        />
      </div>
    </ErrorBoundary>
  );
};

export default Graph;

