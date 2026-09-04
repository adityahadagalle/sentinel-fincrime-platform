import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../hooks/useWebSocket';
import RiskBadge from '../components/RiskBadge';
import InvestigationSidebar from '../components/InvestigationSidebar';
import { getRole } from '../roleStore';
import { Briefcase, Download, Filter, Network } from 'lucide-react';

const FORMATTED_STATUS_MAP = {
  'HIGH_RISK': 'High Risk',
  'CLOSED_FP': 'Closed — False Positive',
  'CLOSED_FALSE_POSITIVE': 'Closed — False Positive',
  'CLOSED_CONFIRMED_FRAUD': 'Closed — Confirmed Fraud',
  'ENHANCED_MONITORING': 'Enhanced Monitoring',
  'REJECT_TRANSACTION': 'Reject Transaction',
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

const formatStatusLabel = (val) => {
  if (!val) return '';
  if (FORMATTED_STATUS_MAP[val]) return FORMATTED_STATUS_MAP[val];
  return String(val).replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
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

  // Check if case is actioned
  const hasAnyAction = (c?.actionLog && c.actionLog.length > 0) ||
    (c?.actions_taken && c.actions_taken.length > 0) ||
    (actions && actions.some(a => a.case_id === c.case_id)) ||
    (transactions && transactions.some(t => t.case_id === c.case_id && (
      t.account_status === 'FROZEN' || t.account_status === 'BLOCKED' || 
      t.action === 'FREEZE' || t.action === 'BLOCK' || 
      (t.execution_record && t.execution_record.action_executed)
    ))) ||
    (c?.nodes && c.nodes.some(n => n.status === 'FROZEN' || n.status === 'BLOCKED'));

  if (
    statusStr === 'ACTIONED' || statusStr === 'MONITORING' || 
    statusStr === 'ENHANCED_MONITORING' || statusStr === 'FROZEN' || 
    statusStr === 'BLOCKED' || statusStr === 'CDD_PENDING' || 
    statusStr === 'UNDER_REVIEW' || statusStr === 'ESCALATED' ||
    statusStr === 'INVESTIGATING' || hasAnyAction
  ) {
    if (statusStr === 'FROZEN' || (transactions && transactions.some(t => t.case_id === c.case_id && t.account_status === 'FROZEN'))) {
      return 'FROZEN';
    }
    return 'ACTIONED';
  }

  // Check if high risk
  const score = Number(c?.risk_level || c?.risk_score || 0);
  if (statusStr === 'HIGH_RISK' || score >= 70 || statusStr === 'CRITICAL') {
    return 'HIGH_RISK';
  }

  return 'NEW';
};

const Cases = () => {
  const navigate = useNavigate();
  const { cases, actions, transactions } = useWebSocket();
  const [filter, setFilter] = useState('ALL');
  const [sidebarState, setSidebarState] = useState({ isOpen: false, case: null, tx: null, actions: [] });
  const role = getRole();

  const QUEUE_FILTERS = ['ALL', 'NEW', 'HIGH RISK', 'ACTIONED', 'CLOSED'];

  // Categorize every case with its authoritative effective status
  const casesWithStatus = React.useMemo(() => {
    return cases.map(c => ({
      ...c,
      effectiveStatus: getCaseEffectiveStatus(c, actions, transactions)
    }));
  }, [cases, actions, transactions]);

  // Tab counts for all queues
  const filterCounts = React.useMemo(() => {
    const counts = {
      'ALL': casesWithStatus.length,
      'NEW': 0,
      'HIGH RISK': 0,
      'ACTIONED': 0,
      'CLOSED': 0
    };
    casesWithStatus.forEach(c => {
      const st = c.effectiveStatus;
      if (st === 'CLOSED') counts['CLOSED']++;
      else if (st === 'ACTIONED' || st === 'FROZEN') counts['ACTIONED']++;
      else if (st === 'HIGH_RISK') counts['HIGH RISK']++;
      else counts['NEW']++;
    });
    return counts;
  }, [casesWithStatus]);

  const filteredCases = React.useMemo(() => {
    return casesWithStatus.filter(c => {
      if (filter === 'ALL') return true;
      if (filter === 'NEW') return c.effectiveStatus === 'NEW';
      if (filter === 'HIGH RISK') return c.effectiveStatus === 'HIGH_RISK';
      if (filter === 'ACTIONED') return c.effectiveStatus === 'ACTIONED' || c.effectiveStatus === 'FROZEN';
      if (filter === 'CLOSED') return c.effectiveStatus === 'CLOSED';
      return true;
    });
  }, [casesWithStatus, filter]);

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
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all border ${
                role === "admin"
                  ? 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 shadow-sm'
                  : 'opacity-40 grayscale cursor-not-allowed bg-slate-900 border-slate-800 text-slate-500'
              }`}
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Audit Log</span>
            </button>
          </div>
        </header>

        {/* Filter Bar */}
        <div className="flex items-center justify-between gap-4 p-2 bg-card border border-border/80 rounded-xl overflow-x-auto">
          <div className="flex items-center gap-1.5 min-w-max">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 px-3 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Filter:
            </span>
            {QUEUE_FILTERS.map(f => {
              const count = filterCounts[f] !== undefined ? filterCounts[f] : 0;
              return (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all flex items-center gap-1.5 ${
                    filter === f 
                      ? 'bg-primary text-white shadow-sm' 
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  <span>{f}</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono font-bold ${
                    filter === f ? 'bg-white/20 text-white' : 'bg-slate-800 text-slate-400'
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
                          {filter === 'HIGH RISK' && 'No high-risk cases currently require immediate triage.'}
                          {filter === 'NEW' && 'No new un-triaged cases in queue.'}
                        </span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredCases.map((c) => {
                    const effStatus = c.effectiveStatus || c.status;
                    const isClosed = effStatus === 'CLOSED';
                    const isFrozen = effStatus === 'FROZEN';
                    const isActioned = effStatus === 'ACTIONED';
                    const isHigh = effStatus === 'HIGH_RISK';

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
                          <span className={`text-[11px] font-medium px-2.5 py-0.5 rounded border ${
                            isClosed
                              ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                              : isFrozen
                              ? 'bg-rose-950/80 text-rose-300 border-rose-600/60 font-bold'
                              : isActioned
                              ? 'bg-sky-500/15 text-sky-400 border-sky-500/30 font-semibold'
                              : isHigh
                              ? 'bg-rose-500/15 text-rose-400 border-rose-500/30' 
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

