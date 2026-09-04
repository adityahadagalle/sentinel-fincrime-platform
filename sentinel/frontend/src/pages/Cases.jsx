import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../hooks/useWebSocket';
import RiskBadge from '../components/RiskBadge';
import InvestigationSidebar from '../components/InvestigationSidebar';
import { getRole } from '../roleStore';
import { Briefcase, Download, Filter, Network, Zap, UserCheck } from 'lucide-react';

const FORMATTED_STATUS_MAP = {
  'HIGH_RISK': 'High Risk',
  'CLOSED_FP': 'Closed — False Positive',
  'CLOSED_FALSE_POSITIVE': 'Closed — False Positive',
  'CLOSED_CONFIRMED_FRAUD': 'Closed — Confirmed Fraud',
  'ENHANCED_MONITORING': 'Enhanced Monitoring',
  'REJECT_TRANSACTION': 'Reject Transaction',
  'ESCALATE_ANALYST_REVIEW': 'Escalate Analyst Review',
  'MARK_FALSE_POSITIVE': 'Mark False Positive',
  'CLOSE_ACCOUNT': 'Close Account',
  'FILE_STR': 'File STR',
  'AUTOMATION_ENGINE': 'Automation Engine',
  'HUMAN_OPERATOR': 'Human Operator',
  'DO_NOT_EXECUTE': 'Do Not Execute',
  'POLICY_BLOCKED': 'Policy Blocked',
  'MONITORING': 'Monitoring',
  'ACTIONED': 'Actioned',
  'CLOSED': 'Closed',
  'NEW': 'New',
  'FROZEN': 'Frozen',
  'BLOCKED': 'Blocked',
};

const ACTION_LABELS = {
  'MONITOR': 'Monitor',
  'ENHANCED_MONITORING': 'Enhanced Monitoring',
  'MARK_FALSE_POSITIVE': 'Mark False Positive',
  'ESCALATE_ANALYST_REVIEW': 'Escalate Analyst Review',
  'BLOCK': 'Block',
  'REJECT_TRANSACTION': 'Reject Transaction',
  'FILE_STR': 'File STR',
  'CLOSE_ACCOUNT': 'Close Account',
  'FREEZE': 'Freeze',
};

const formatStatusLabel = (val) => {
  if (!val) return '';
  if (ACTION_LABELS[val]) return ACTION_LABELS[val];
  if (FORMATTED_STATUS_MAP[val]) return FORMATTED_STATUS_MAP[val];
  return String(val).replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

export const getCaseActionDetails = (c, actions = [], transactions = []) => {
  const caseId = c.case_id;
  const rawList = [];

  // 1. Check c.actionLog (Authoritative log of executed actions)
  if (Array.isArray(c?.actionLog)) {
    c.actionLog.forEach(item => {
      const act = String(item.action_type || item.action || '').toUpperCase();
      const status = String(item.status || item.execution_status || item.action_status || '').toUpperCase();
      const isSuccess = status === 'SUCCESS' || status === 'COMPLETED' || status === 'EXECUTED' || status === 'ACTIVE';
      if (act && isSuccess) {
        const actor = String(item.actor_type || item.actor || item.analyst_role || '').toUpperCase();
        rawList.push({ action: act, actor_type: actor });
      }
    });
  }

  // 2. Check c.actions_taken (Explicitly recorded executed actions)
  if (Array.isArray(c?.actions_taken)) {
    c.actions_taken.forEach(item => {
      if (typeof item === 'string') {
        rawList.push({ action: item.toUpperCase(), actor_type: '' });
      } else if (item && typeof item === 'object') {
        const act = String(item.action || item.action_type || '').toUpperCase();
        const actor = String(item.actor_type || item.actor || '').toUpperCase();
        const status = String(item.status || item.execution_status || item.action_status || '').toUpperCase();
        const isSuccess = status === 'SUCCESS' || status === 'COMPLETED' || status === 'EXECUTED' || status === 'ACTIVE';
        if (act && isSuccess) {
          rawList.push({ action: act, actor_type: actor });
        }
      }
    });
  }

  // 3. Check WebSocket actions (Broadcasted executed action events)
  if (Array.isArray(actions)) {
    actions.forEach(a => {
      if (a.case_id === caseId) {
        const act = String(a.action || a.action_type || '').toUpperCase();
        const actor = String(a.actor_type || a.actor || '').toUpperCase();
        const status = String(a.action_status || a.execution_status || '').toUpperCase();
        const isSuccess = status === 'SUCCESS' || status === 'COMPLETED' || status === 'EXECUTED';
        if (act && isSuccess) {
          rawList.push({ action: act, actor_type: actor });
        }
      }
    });
  }

  // 4. Check WebSocket transactions (Only count if action execution succeeded or account state changed)
  if (Array.isArray(transactions)) {
    transactions.forEach(t => {
      if (t.case_id === caseId) {
        const rec = t.execution_record || {};
        const execStatus = String(rec.execution_status || '').toUpperCase();
        const isExecuted = execStatus === 'SUCCESS' || execStatus === 'EXECUTED' || rec.action_executed === true;
        const status = String(t.account_status || rec.resulting_account_state || '').toUpperCase();

        if (isExecuted) {
          const act = String(rec.action_code || t.action || '').toUpperCase();
          const actor = String(rec.actor_type || t.actor_type || '').toUpperCase();
          if (act) rawList.push({ action: act, actor_type: actor });
        } else if (status === 'FROZEN') {
          rawList.push({ action: 'FREEZE', actor_type: 'HUMAN_OPERATOR' });
        } else if (status === 'BLOCKED') {
          rawList.push({ action: 'BLOCK', actor_type: rec.actor_type || 'AUTOMATION_ENGINE' });
        }
      }
    });
  }

  // 5. Explicit case status (Only if case status itself indicates executed action)
  const cStatus = String(c?.status || '').toUpperCase();
  if (cStatus === 'FROZEN') {
    rawList.push({ action: 'FREEZE', actor_type: 'HUMAN_OPERATOR' });
  } else if (cStatus === 'BLOCKED') {
    rawList.push({ action: 'BLOCK', actor_type: 'AUTOMATION_ENGINE' });
  }

  const resolved = [];
  const seenKeys = new Set();

  rawList.forEach(item => {
    let code = item.action;
    if (code === 'CLOSE_FP' || code === 'CLOSED_FP' || code === 'DISMISS_CASE') code = 'MARK_FALSE_POSITIVE';
    if (code === 'FLAG' || code === 'ESCALATE') code = 'ESCALATE_ANALYST_REVIEW';
    if (code === 'REJECT') code = 'REJECT_TRANSACTION';
    if (code === 'CLOSE') code = 'CLOSE_ACCOUNT';

    // Governance Rule: FREEZE is ALWAYS HUMAN_OPERATOR (Manual)
    let isManual = false;
    if (code === 'FREEZE') {
      isManual = true;
    } else {
      const actorStr = item.actor_type;
      isManual = actorStr === 'HUMAN_OPERATOR' || actorStr === 'HUMAN OPERATOR' || actorStr === 'OPERATOR' || actorStr === 'ANALYST';
    }

    const key = `${code}_${isManual ? 'MANUAL' : 'AUTO'}`;
    if (!seenKeys.has(key)) {
      seenKeys.add(key);
      resolved.push({
        actionCode: code,
        isManual,
        actorType: isManual ? 'HUMAN_OPERATOR' : 'AUTOMATION_ENGINE'
      });
    }
  });

  return resolved;
};

export const getCaseEffectiveStatus = (c, actions = [], transactions = []) => {
  const statusStr = String(c?.status || '').toUpperCase();
  const dispositionCode = String(c?.last_disposition_code || '').toUpperCase();

  // Check if case is closed
  const hasCloseAction = (c?.actionLog && c.actionLog.some(a => {
    const act = String(a.action_type || a.action || '').toUpperCase();
    return act.includes('CLOSE') || act.includes('DISMISS') || act.includes('RESOLVE') || act.includes('APPROVE');
  })) || (actions && actions.some(a => {
    if (a.case_id !== c.case_id) return false;
    const act = String(a.action || a.action_type || '').toUpperCase();
    return act.includes('CLOSE') || act.includes('DISMISS') || act.includes('RESOLVE') || act.includes('APPROVE');
  }));

  if (
    statusStr === 'CLOSED' || statusStr === 'CLOSED_FP' ||
    statusStr === 'CLOSED_CONFIRMED_FRAUD' || statusStr === 'CLOSED_FALSE_POSITIVE' ||
    statusStr === 'RESOLVED_DISMISSED' || statusStr === 'RESOLVED_APPROVED' ||
    statusStr.includes('CLOSE') || dispositionCode === 'DISMISS_CASE' ||
    dispositionCode === 'APPROVE_TRANSACTION' || hasCloseAction
  ) {
    return 'CLOSED';
  }

  // Check if case has actual executed actions
  const actionDetails = getCaseActionDetails(c, actions, transactions);
  const hasExecutedAction = actionDetails.length > 0;

  if (hasExecutedAction || statusStr === 'FROZEN' || statusStr === 'BLOCKED') {
    return 'ACTIONED';
  }

  return 'NEW';
};

const Cases = () => {
  const navigate = useNavigate();
  const { cases, actions, transactions } = useWebSocket();
  const [filter, setFilter] = useState('ALL');
  const [actionedSubFilter, setActionedSubFilter] = useState('ALL_ACTIONED');
  const [sidebarState, setSidebarState] = useState({ isOpen: false, case: null, tx: null, actions: [] });
  const role = getRole();

  // Final primary filters: ALL, NEW, ACTIONED, CLOSED (HIGH RISK removed)
  const QUEUE_FILTERS = ['ALL', 'NEW', 'ACTIONED', 'CLOSED'];

  // Categorize every case with its authoritative effective status and action details
  const casesWithStatus = useMemo(() => {
    return cases.map(c => {
      const effStatus = getCaseEffectiveStatus(c, actions, transactions);
      const actionDetails = getCaseActionDetails(c, actions, transactions);
      return {
        ...c,
        effectiveStatus: effStatus,
        actionDetails
      };
    });
  }, [cases, actions, transactions]);

  // Tab counts for primary queues
  const filterCounts = useMemo(() => {
    const counts = {
      'ALL': casesWithStatus.length,
      'NEW': 0,
      'ACTIONED': 0,
      'CLOSED': 0
    };
    casesWithStatus.forEach(c => {
      const st = c.effectiveStatus;
      if (st === 'CLOSED') counts['CLOSED']++;
      else if (st === 'ACTIONED') counts['ACTIONED']++;
      else counts['NEW']++;
    });
    return counts;
  }, [casesWithStatus]);

  // Breakdown of automatic vs manual actions across actioned cases
  const actionedBreakdown = useMemo(() => {
    const autoCounts = {};
    const manualCounts = {};
    let totalAutoCases = 0;
    let totalManualCases = 0;

    casesWithStatus.forEach(c => {
      if (c.effectiveStatus === 'ACTIONED') {
        let caseHasAuto = false;
        let caseHasManual = false;

        c.actionDetails.forEach(act => {
          if (act.isManual) {
            caseHasManual = true;
            manualCounts[act.actionCode] = (manualCounts[act.actionCode] || 0) + 1;
          } else {
            caseHasAuto = true;
            autoCounts[act.actionCode] = (autoCounts[act.actionCode] || 0) + 1;
          }
        });

        if (caseHasAuto) totalAutoCases++;
        if (caseHasManual) totalManualCases++;
      }
    });

    return {
      autoCounts,
      manualCounts,
      totalAutoCases,
      totalManualCases
    };
  }, [casesWithStatus]);

  // Filtered cases list based on primary filter and actioned sub-filter
  const filteredCases = useMemo(() => {
    return casesWithStatus.filter(c => {
      if (filter === 'ALL') return true;
      if (filter === 'NEW') return c.effectiveStatus === 'NEW';
      if (filter === 'CLOSED') return c.effectiveStatus === 'CLOSED';
      if (filter === 'ACTIONED') {
        if (c.effectiveStatus !== 'ACTIONED') return false;
        if (actionedSubFilter === 'ALL_ACTIONED') return true;
        if (actionedSubFilter === 'ALL_AUTO') return c.actionDetails.some(a => !a.isManual);
        if (actionedSubFilter === 'ALL_MANUAL') return c.actionDetails.some(a => a.isManual);
        if (actionedSubFilter.startsWith('AUTO_')) {
          const code = actionedSubFilter.replace('AUTO_', '');
          return c.actionDetails.some(a => !a.isManual && a.actionCode === code);
        }
        if (actionedSubFilter.startsWith('MANUAL_')) {
          const code = actionedSubFilter.replace('MANUAL_', '');
          return c.actionDetails.some(a => a.isManual && a.actionCode === code);
        }
        return true;
      }
      return true;
    });
  }, [casesWithStatus, filter, actionedSubFilter]);

  const handleRowClick = (c) => {
    const relatedTx = transactions.find(t => t.case_id === c.case_id);
    const relatedActions = actions.filter(a => a.case_id === c.case_id);
    setSidebarState({ isOpen: true, case: c, tx: relatedTx, actions: relatedActions });
  };

  const handleExportAuditLog = async () => {
    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${API_BASE}/export/sentinel_audit.csv`);
      if (!res.ok) {
        console.error(`Audit export failed: HTTP ${res.status}`);
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const now = new Date();
      const pad = (n) => String(n).padStart(2, '0');
      const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}`;
      const filename = `SENTINEL_Audit_Log_${dateStr}.csv`;
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Audit export network error:', err);
    }
  };

  return (
    <div className="p-8 bg-background min-h-full font-sans">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Page Header */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Briefcase className="w-6 h-6 text-sky-400" />
              Case Management Queue
            </h1>
            <p className="text-xs text-slate-400 mt-1">Investigation workflows, status tracking, and authoritative audit logging</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleExportAuditLog}
              disabled={role !== "admin"}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all border ${role === "admin"
                  ? 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 shadow-sm'
                  : 'opacity-40 grayscale cursor-not-allowed bg-slate-900 border-slate-800 text-slate-500'
                }`}
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Audit Log</span>
            </button>
          </div>
        </header>

        {/* Primary Filter Bar */}
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-4 p-2.5 bg-card border border-border/80 rounded-xl overflow-x-auto">
            <div className="flex items-center gap-2 min-w-max">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 px-3 flex items-center gap-1">
                <Filter className="w-3.5 h-3.5" /> FILTER:
              </span>
              {QUEUE_FILTERS.map(f => {
                const count = filterCounts[f] !== undefined ? filterCounts[f] : 0;
                return (
                  <button
                    key={f}
                    onClick={() => {
                      setFilter(f);
                      if (f === 'ACTIONED') setActionedSubFilter('ALL_ACTIONED');
                    }}
                    className={`px-4 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all flex items-center gap-2 ${filter === f
                        ? 'bg-primary text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                      }`}
                  >
                    <span>{f}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold ${filter === f ? 'bg-white/20 text-white' : 'bg-slate-800 text-slate-400'
                      }`}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
            <span className="text-xs font-mono text-slate-400 px-3 whitespace-nowrap">
              {filteredCases.length} {filteredCases.length === 1 ? 'case' : 'cases'}
            </span>
          </div>

          {/* Action Categorization Sub-Filter (shown when ACTIONED tab is selected) */}
          {filter === 'ACTIONED' && (
            <div className="p-4 bg-card/90 border border-border/80 rounded-xl space-y-3 font-mono shadow-md">
              {/* Category Header */}
              <div className="flex items-center justify-between border-b border-border/60 pb-2">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  Action Classification & Categorization
                </span>
                <button
                  onClick={() => setActionedSubFilter('ALL_ACTIONED')}
                  className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${actionedSubFilter === 'ALL_ACTIONED'
                      ? 'bg-slate-700 text-white border border-slate-500'
                      : 'text-slate-400 hover:text-slate-200'
                    }`}
                >
                  All Actioned ({filterCounts['ACTIONED']})
                </button>
              </div>

              {/* AUTOMATIC ACTIONS */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] font-bold text-sky-400 uppercase tracking-wider px-2.5 py-1 rounded bg-sky-950/70 border border-sky-800/60 flex items-center gap-1 shrink-0">
                  <Zap className="w-3 h-3 text-sky-400" />
                  AUTOMATIC ACTIONS ({actionedBreakdown.totalAutoCases})
                </span>
                <button
                  onClick={() => setActionedSubFilter('ALL_AUTO')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${actionedSubFilter === 'ALL_AUTO'
                      ? 'bg-sky-600 text-white font-bold shadow-sm'
                      : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700 border border-slate-700/60'
                    }`}
                >
                  All Automatic ({actionedBreakdown.totalAutoCases})
                </button>
                {Object.entries(actionedBreakdown.autoCounts).map(([code, count]) => (
                  <button
                    key={`auto_${code}`}
                    onClick={() => setActionedSubFilter(`AUTO_${code}`)}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-all flex items-center gap-1.5 ${actionedSubFilter === `AUTO_${code}`
                        ? 'bg-sky-600 text-white font-bold shadow-sm'
                        : 'bg-slate-800/50 text-slate-300 border border-slate-700/60 hover:bg-slate-700'
                      }`}
                  >
                    <span>{ACTION_LABELS[code] || formatStatusLabel(code)}</span>
                    <span className="px-1.5 py-0.2 rounded-full bg-slate-900 text-sky-300 text-[10px] font-bold">
                      {count}
                    </span>
                  </button>
                ))}
              </div>

              {/* MANUAL ACTIONS */}
              <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-border/40">
                <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider px-2.5 py-1 rounded bg-purple-950/70 border border-purple-800/60 flex items-center gap-1 shrink-0">
                  <UserCheck className="w-3 h-3 text-purple-400" />
                  MANUAL ACTIONS ({actionedBreakdown.totalManualCases})
                </span>
                <button
                  onClick={() => setActionedSubFilter('ALL_MANUAL')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${actionedSubFilter === 'ALL_MANUAL'
                      ? 'bg-purple-600 text-white font-bold shadow-sm'
                      : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700 border border-slate-700/60'
                    }`}
                >
                  All Manual ({actionedBreakdown.totalManualCases})
                </button>
                {Object.entries(actionedBreakdown.manualCounts).map(([code, count]) => (
                  <button
                    key={`manual_${code}`}
                    onClick={() => setActionedSubFilter(`MANUAL_${code}`)}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-all flex items-center gap-1.5 ${actionedSubFilter === `MANUAL_${code}`
                        ? 'bg-purple-600 text-white font-bold shadow-sm'
                        : 'bg-slate-800/50 text-slate-300 border border-slate-700/60 hover:bg-slate-700'
                      }`}
                  >
                    <span>{ACTION_LABELS[code] || formatStatusLabel(code)}</span>
                    <span className="px-1.5 py-0.2 rounded-full bg-slate-900 text-purple-300 text-[10px] font-bold">
                      {count}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Table Container */}
        <div className="rounded-xl border border-border/80 bg-card overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[900px]">
              <thead>
                <tr className="bg-muted/60 text-[10px] uppercase tracking-wider font-semibold text-slate-400 border-b border-border/80 select-none">
                  <th className="py-3.5 px-4">Case ID</th>
                  <th className="py-3.5 px-4">Primary Transaction</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-center">Risk Level</th>
                  <th className="py-3.5 px-4 text-right">Fraud Value</th>
                  <th className="py-3.5 px-4 text-right">Recoverable</th>
                  <th className="py-3.5 px-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {filteredCases.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-16 text-center text-slate-400 font-mono text-xs">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <Briefcase className="w-8 h-8 text-slate-600 mb-1" />
                        <span className="text-slate-300 font-bold text-sm">No cases in {filter} queue</span>
                        <span className="text-slate-500 max-w-sm text-center">
                          {filter === 'ACTIONED' && 'Cases with executed automated policies or operator interventions (Freeze, Flag, Monitor) will appear here.'}
                          {filter === 'CLOSED' && 'Cases resolved or dismissed via the investigation workstation will appear here.'}
                          {filter === 'NEW' && 'No new un-triaged cases in queue.'}
                          {filter === 'ALL' && 'No cases currently registered.'}
                        </span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredCases.map((c) => {
                    const effStatus = c.effectiveStatus || c.status;
                    const isClosed = effStatus === 'CLOSED';
                    const isActioned = effStatus === 'ACTIONED';

                    return (
                      <tr
                        key={c.case_id}
                        onClick={() => handleRowClick(c)}
                        className="hover:bg-slate-800/40 transition-colors cursor-pointer border-b border-border/60"
                      >
                        <td className="py-3.5 px-4 font-mono text-xs font-semibold text-slate-200">
                          {c.case_id}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-xs text-slate-400">
                          {role === "admin" ? (c.primary_tx_id || 'N/A') : '••••••••'}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`text-[11px] font-medium px-2.5 py-0.5 rounded border ${isClosed
                              ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                              : isActioned
                                ? 'bg-sky-500/15 text-sky-400 border-sky-500/30 font-semibold'
                                : 'bg-slate-800 text-slate-300 border-slate-700/60'
                            }`}>
                            {formatStatusLabel(effStatus)}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <RiskBadge score={c.risk_level} />
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono text-sm font-semibold text-slate-100">
                          ₹{(c.total_fraud_amount || 0).toLocaleString()}
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono text-sm font-semibold text-emerald-400">
                          ₹{(c.recoverable_amount || 0).toLocaleString()}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <div className="flex justify-center items-center gap-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                const url = c.primary_tx_id ? `/graph/${c.case_id}?tx=${c.primary_tx_id}` : `/graph/${c.case_id}`;
                                navigate(url);
                              }}
                              className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700/60 transition-colors"
                              title="Open Contextual Investigation Graph"
                            >
                              <Network className="w-3 h-3 text-sky-400" />
                              <span>Graph</span>
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleRowClick(c); }}
                              className="flex items-center gap-1 px-2.5 py-1 rounded bg-primary hover:bg-primary/90 text-white text-xs font-semibold transition-colors shadow-sm"
                            >
                              <span>Analyze</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <InvestigationSidebar
        isOpen={sidebarState.isOpen}
        selectedCase={sidebarState.case ? cases.find(c => c.case_id === sidebarState.case.case_id) : null}
        selectedTransaction={sidebarState.tx}
        actions={sidebarState.case ? actions.filter(a => a.case_id === sidebarState.case.case_id) : []}
        onClose={() => setSidebarState({ ...sidebarState, isOpen: false })}
        role={role}
      />
    </div>
  );
};

export default Cases;
