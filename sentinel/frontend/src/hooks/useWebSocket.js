import { useEffect, useState } from 'react';
import { EVENT_TYPES } from '../types/events';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const initialState = {
  transactions: [],
  cases: [],
  actions: [],
  connectionStatus: 'OFFLINE',
  lastTxEvent: null
};


let store = { ...initialState };
const listeners = new Set();
let ws = null;
let reconnectTimer = null;
let pollingTimer = null;
let reconnectDelay = 1500;
let started = false;
let pollingFailures = 0;

const notify = () => {
  listeners.forEach((listener) => listener(store));
};

const setStore = (updater) => {
  store = typeof updater === 'function' ? updater(store) : updater;
  notify();
};

const normalizeCase = (raw = {}) => ({
  case_id: raw.case_id || raw.caseId || '',
  status: raw.status || 'NEW',
  nodes: Array.isArray(raw.nodes)
    ? raw.nodes.map((n) => ({
      ...n,
      accountId: n.accountId || n.account_id || n.id || '',
      account_id: n.account_id || n.accountId || n.id || '',
      id: n.id || n.accountId || n.account_id || ''
    }))
    : [],
  edges: Array.isArray(raw.edges)
    ? raw.edges.map((e) => ({
      ...e,
      source: e.source || e.from || '',
      target: e.target || e.to || '',
      tx_id: e.tx_id || e.id || `${e.source || e.from}-${e.target || e.to}`
    }))
    : [],
  recoverable_amount: Number(raw.recoverable_amount || raw.recoverableAmount || 0),
  actionLog: Array.isArray(raw.actionLog)
    ? raw.actionLog.map(normalizeAction)
    : (Array.isArray(raw.actions_taken) ? raw.actions_taken.map(normalizeAction) : []),
  risk_level: Number(raw.risk_level || 0),
  golden_window_minutes: Number(raw.golden_window_minutes || 0),
  total_fraud_amount: Number(raw.total_fraud_amount || 0),
  primary_tx_id: raw.primary_tx_id || raw.primaryTxId || '',
  chain: Array.isArray(raw.chain) ? raw.chain : []
});

const normalizeTransaction = (raw = {}) => ({
  ...raw,
  tx_id: raw.tx_id || raw.txId || '',
  case_id: raw.case_id || raw.caseId || '',
  risk_score: Number(raw.risk_score || 0),
  timestamp: raw.timestamp || new Date().toISOString()
});

const normalizeAction = (raw = {}) => ({
  ...raw,
  action_id: raw.action_id || raw.actionId || `action_${Date.now()}`,
  case_id: raw.case_id || raw.caseId || '',
  action_type: (raw.action_type || raw.actionType || raw.action || '').toUpperCase(),
  target_id: raw.target_id || raw.target || raw.account_id || raw.accountId || 'GLOBAL',
  target: raw.target || raw.target_id || raw.account_id || raw.accountId || 'GLOBAL',
  timestamp: raw.timestamp || new Date().toISOString()
});

const mergeCase = (cases, incomingRaw) => {
  const incoming = normalizeCase(incomingRaw);
  const idx = cases.findIndex((c) => c.case_id === incoming.case_id);
  if (idx === -1) return [incoming, ...cases];
  const next = [...cases];
  next[idx] = { ...next[idx], ...incoming };
  return next;
};

const validateCasePayload = (raw) => {
  if (!raw || typeof raw !== 'object') {
    console.warn('[WS] Malformed case payload: expected object');
    return false;
  }
  if (!raw.case_id && !raw.caseId) {
    console.warn('[WS] Malformed case payload: missing case_id');
    return false;
  }
  if (raw.nodes !== undefined && !Array.isArray(raw.nodes)) {
    console.warn(`[WS] Malformed case payload for ${raw.case_id || raw.caseId}: nodes must be an array`);
    return false;
  }
  if (raw.edges !== undefined && !Array.isArray(raw.edges)) {
    console.warn(`[WS] Malformed case payload for ${raw.case_id || raw.caseId}: edges must be an array`);
    return false;
  }
  return true;
};

const startPolling = () => {
  if (pollingTimer) return;
  setStore((prev) => ({ ...prev, connectionStatus: 'POLLING' }));
  pollingTimer = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/cases`);
      if (!res.ok) {
        pollingFailures += 1;
        if (pollingFailures >= 3) {
          setStore((prev) => ({ ...prev, connectionStatus: 'OFFLINE' }));
        }
        return;
      }
      const payload = await res.json();
      const cases = Array.isArray(payload)
        ? payload.filter(validateCasePayload).map(normalizeCase)
        : [];
      pollingFailures = 0;
      setStore((prev) => ({ ...prev, cases }));
    } catch {
      pollingFailures += 1;
      if (pollingFailures >= 3) {
        setStore((prev) => ({ ...prev, connectionStatus: 'OFFLINE' }));
      }
    }
  }, 2000);
};

const stopPolling = () => {
  if (!pollingTimer) return;
  clearInterval(pollingTimer);
  pollingTimer = null;
};

const scheduleReconnect = () => {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    setStore((prev) => ({ ...prev, connectionStatus: 'RECONNECTING' }));
    connectWS();
  }, reconnectDelay);
  reconnectDelay = Math.min(reconnectDelay * 2, 10000);
};

const handleEvent = (payload = {}) => {
  const type = payload.event;
  if (type === EVENT_TYPES.TX_SCORED) {
    const incoming = normalizeTransaction(payload);
    setStore((prev) => {
      const exists = prev.transactions.some((tx) => tx.tx_id === incoming.tx_id);
      if (exists) return prev;
      return {
        ...prev,
        transactions: [incoming, ...prev.transactions].slice(0, 100),
        lastTxEvent: incoming
      };
    });
    window.dispatchEvent(new CustomEvent('sentinel_alert', { detail: incoming }));
    return;
  }


  if (type === EVENT_TYPES.CASE_UPDATED) {
    if (!validateCasePayload(payload)) return;
    setStore((prev) => ({
      ...prev,
      cases: mergeCase(prev.cases, payload)
    }));
    return;
  }

  if (type === EVENT_TYPES.TRANSACTION_ACTION || type === 'transaction.action') {
    const actionPayload = {
      transaction_id: payload.transaction_id || payload.tx_id || '',
      tx_id: payload.tx_id || payload.transaction_id || '',
      risk_score: Number(payload.risk_score || 0),
      risk_level: payload.risk_level || 'LOW',
      action: payload.action || 'MONITOR',
      action_status: payload.action_status || 'COMPLETED',
      reason: payload.reason || '',
      automated: payload.automated !== undefined ? payload.automated : true,
      requires_human_approval: Boolean(payload.requires_human_approval),
      financial_action_status: payload.financial_action_status || 'NOT_APPLICABLE',
      case_id: payload.case_id || '',
      investigation_run_id: payload.investigation_run_id || '',
      timestamp: payload.timestamp || new Date().toISOString()
    };
    setStore((prev) => {
      const updatedTxList = prev.transactions.map((t) => {
        if (t.tx_id === actionPayload.tx_id) {
          return {
            ...t,
            response_decision: actionPayload,
            action: actionPayload.action,
            action_status: actionPayload.action_status,
            requires_human_approval: actionPayload.requires_human_approval,
            financial_action_status: actionPayload.financial_action_status
          };
        }
        return t;
      });
      return {
        ...prev,
        transactions: updatedTxList,
        actions: [actionPayload, ...prev.actions]
      };
    });
    window.dispatchEvent(new CustomEvent('sentinel_transaction_action', { detail: actionPayload }));
    return;
  }

  if (type === EVENT_TYPES.AUTOMATION_MODE_CHANGED || type === 'automation.mode.changed') {
    setStore((prev) => ({
      ...prev,
      automation_mode: Boolean(payload.automate_mode)
    }));
    window.dispatchEvent(new CustomEvent('sentinel_automation_mode_changed', { detail: payload }));
    return;
  }

  if (
    type === 'automation.action.executed' ||
    type === 'automation.action.requires_operator' ||
    type === 'automation.action.blocked' ||
    type === 'automation.action.failed' ||
    type === EVENT_TYPES.AUTOMATION_ACTION ||
    type === 'automation.action'
  ) {
    const txId = payload.transaction_id || payload.tx_id;
    const execRec = payload.execution_result || {};
    const accStatus = execRec.resulting_account_state || payload.account_status;

    if (txId) {
      setStore((prev) => {
        const updatedTxList = prev.transactions.map((t) => {
          if (t.tx_id === txId) {
            return {
              ...t,
              account_status: accStatus || t.account_status,
              execution_record: { ...t.execution_record, ...execRec },
              action: payload.action_code || execRec.action_code || t.action,
              action_status: payload.execution_status || execRec.execution_status || t.action_status
            };
          }
          return t;
        });
        return {
          ...prev,
          transactions: updatedTxList
        };
      });
    }
    window.dispatchEvent(new CustomEvent('sentinel_automation_action', { detail: payload }));
    return;
  }



  if (type === EVENT_TYPES.ACTION_TAKEN) {
    const incoming = normalizeAction(payload);
    setStore((prev) => ({
      ...prev,
      actions: [incoming, ...prev.actions],
      cases: prev.cases.map((c) =>
        c.case_id === incoming.case_id
          ? { ...c, actionLog: [incoming, ...(c.actionLog || [])] }
          : c
      )
    }));
  }
};


const connectWS = () => {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    reconnectDelay = 1500;
    stopPolling();
    setStore((prev) => ({ ...prev, connectionStatus: 'LIVE' }));
  };

  ws.onmessage = (event) => {
    try {
      handleEvent(JSON.parse(event.data));
    } catch {
      // ignore malformed payloads
    }
  };

  ws.onclose = () => {
    ws = null;
    startPolling();
    scheduleReconnect();
  };

  ws.onerror = () => {
    ws?.close();
  };
};

const startRealtime = async () => {
  if (started) return;
  started = true;
  startPolling();
  connectWS();
};

const stopRealtime = () => {
  if (ws) {
    ws.onclose = null;
    ws.onerror = null;
    ws.onmessage = null;
    ws.close();
    ws = null;
  }
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  stopPolling();
  started = false;
  reconnectDelay = 1500;
  pollingFailures = 0;
};

export const useWebSocket = () => {
  const [state, setState] = useState(store);

  useEffect(() => {
    listeners.add(setState);
    startRealtime();
    return () => {
      listeners.delete(setState);
      if (listeners.size === 0) {
        stopRealtime();
      }
    };
  }, []);

  return state;
};
