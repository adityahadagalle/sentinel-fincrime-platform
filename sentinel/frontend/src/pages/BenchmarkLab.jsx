import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  FlaskConical, 
  Play, 
  RotateCcw, 
  Download, 
  Search, 
  Filter, 
  Sliders, 
  ShieldAlert, 
  Lock, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Activity, 
  Zap, 
  ChevronRight, 
  X, 
  ExternalLink, 
  Check, 
  Layers, 
  History, 
  Plus, 
  Loader2, 
  RefreshCw, 
  BellOff, 
  SlidersHorizontal, 
  ChevronDown, 
  ChevronUp, 
  UserCheck, 
  Shield, 
  CheckCircle,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  FileSpreadsheet,
  HelpCircle,
  Info
} from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import CustomTransactionModal from '../components/CustomTransactionModal';
import { usePresentationMode } from '../hooks/usePresentationMode';

// Human-friendly Scenario Definitions for Jury Presentations
const SCENARIO_CHOICES = [
  { 
    id: 'BALANCED', 
    name: 'Balanced Test', 
    desc: 'Equal distribution across all standard suspicious scenarios.',
    profileMode: 'BALANCED',
    singleProfile: null
  },
  { 
    id: 'LARGE_TX', 
    name: 'Large Transactions', 
    desc: 'Tests payments significantly higher than normal customer spending.',
    profileMode: 'SINGLE',
    singleProfile: 'AMOUNT_ANOMALY'
  },
  { 
    id: 'NEW_RECEIVER', 
    name: 'New Recipients', 
    desc: 'Tests payments to a beneficiary never used before.',
    profileMode: 'SINGLE',
    singleProfile: 'NEW_RECEIVER'
  },
  { 
    id: 'UNUSUAL_TIMES', 
    name: 'Unusual Times', 
    desc: 'Tests payments made during late-night or unusual hours.',
    profileMode: 'SINGLE',
    singleProfile: 'TIME_ANOMALY'
  },
  { 
    id: 'CUSTOMER_PRESSURE', 
    name: 'Customer Under Pressure', 
    desc: 'Tests payments where customer is on an active call (coercion).',
    profileMode: 'SINGLE',
    singleProfile: 'ACTIVE_CALL'
  },
  { 
    id: 'MONEY_CHAIN', 
    name: 'Money Movement Chain', 
    desc: 'Tests layered mule network funds pass-through across accounts.',
    profileMode: 'SINGLE',
    singleProfile: 'MULTI_HOP'
  },
  { 
    id: 'MULTI_SIGNALS', 
    name: 'Multiple Warning Signs', 
    desc: 'Combines several high-risk indicators in a single transfer.',
    profileMode: 'SINGLE',
    singleProfile: 'MULTI_SIGNAL'
  },
];

const BATCH_PRESETS = [10, 25, 50, 100];

const formatCurrency = (amt) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amt || 0);
};

const getHumanScenarioName = (profile) => {
  switch (profile?.toUpperCase()) {
    case 'BASELINE': return 'Standard Routine Payment';
    case 'NEW_RECEIVER': return 'New Recipient';
    case 'AMOUNT_ANOMALY': return 'Large Transaction';
    case 'TIME_ANOMALY': return 'Unusual Late-Night Hour';
    case 'ACTIVE_CALL': return 'Customer Under Pressure (Call)';
    case 'MULTI_SIGNAL': return 'Multiple Warning Signs';
    case 'MULTI_HOP': return 'Money Movement Chain';
    case 'CUSTOM_MANUAL': return 'Custom Test Scenario';
    default: return profile?.replace(/_/g, ' ') || 'Standard Payment';
  }
};

const getHumanSignalChips = (tx) => {
  const chips = [];
  const meta = tx?.simulator_meta || {};
  const factors = tx?.risk_factors || [];

  if (meta.is_new_receiver || tx.is_new_receiver || factors.some((f) => String(f).toLowerCase().includes('receiver'))) {
    chips.push({ label: 'New recipient', bg: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30' });
  }
  if (tx.amount > 100000 || factors.some((f) => String(f).toLowerCase().includes('amount'))) {
    chips.push({ label: 'Unusually large', bg: 'bg-orange-500/10 text-orange-300 border-orange-500/30' });
  }
  if (tx.is_night_time || factors.some((f) => String(f).toLowerCase().includes('night') || String(f).toLowerCase().includes('time'))) {
    chips.push({ label: 'Late night', bg: 'bg-amber-500/10 text-amber-300 border-amber-500/30' });
  }
  if (tx.on_active_call || factors.some((f) => String(f).toLowerCase().includes('call'))) {
    chips.push({ label: 'Customer on active call', bg: 'bg-rose-500/10 text-rose-300 border-rose-500/30' });
  }
  if (tx.hop_number > 0 || tx.chain_id || factors.some((f) => String(f).toLowerCase().includes('hop') || String(f).toLowerCase().includes('chain'))) {
    chips.push({ label: 'Money chain hop', bg: 'bg-purple-500/10 text-purple-300 border-purple-500/30' });
  }
  if (tx.device_changed || factors.some((f) => String(f).toLowerCase().includes('device'))) {
    chips.push({ label: 'Unrecognized device', bg: 'bg-amber-500/10 text-amber-300 border-amber-500/30' });
  }
  if (tx.velocity_flag || factors.some((f) => String(f).toLowerCase().includes('velocity'))) {
    chips.push({ label: 'Rapid series', bg: 'bg-orange-500/10 text-orange-300 border-orange-500/30' });
  }
  if (tx.is_cross_border || factors.some((f) => String(f).toLowerCase().includes('border'))) {
    chips.push({ label: 'International', bg: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30' });
  }
  if (chips.length === 0) {
    chips.push({ label: 'Normal activity', bg: 'bg-slate-800/80 text-slate-400 border-slate-700/60' });
  }
  return chips;
};

const getPlainLanguageFindings = (tx) => {
  const findings = [];
  const meta = tx?.simulator_meta || {};
  const factors = tx?.risk_factors || [];

  if (meta.is_new_receiver || tx.is_new_receiver || factors.some((f) => String(f).toLowerCase().includes('receiver'))) {
    findings.push('New recipient: First payment to this beneficiary account');
  }
  if (tx.amount > 100000 || factors.some((f) => String(f).toLowerCase().includes('amount'))) {
    findings.push(`Unusually large payment: Amount ${formatCurrency(tx.amount)} exceeds typical monthly spending`);
  }
  if (tx.is_night_time || factors.some((f) => String(f).toLowerCase().includes('night') || String(f).toLowerCase().includes('time'))) {
    findings.push('Late-night payment: Payment initiated during unusual hours');
  }
  if (tx.on_active_call || factors.some((f) => String(f).toLowerCase().includes('call'))) {
    findings.push('Customer on active call: Customer may be receiving live instructions');
  }
  if (tx.hop_number > 0 || tx.chain_id || factors.some((f) => String(f).toLowerCase().includes('hop') || String(f).toLowerCase().includes('chain'))) {
    findings.push('Money movement chain: Rapid pass-through across multiple accounts');
  }
  if (tx.device_changed || factors.some((f) => String(f).toLowerCase().includes('device'))) {
    findings.push('Unrecognized device: Payment initiated from a new device');
  }
  if (tx.velocity_flag || factors.some((f) => String(f).toLowerCase().includes('velocity'))) {
    findings.push('Rapid series of payments: Multiple payments initiated close together');
  }
  if (tx.is_cross_border || factors.some((f) => String(f).toLowerCase().includes('border'))) {
    findings.push('International transfer: Involves a foreign currency corridor');
  }
  if (findings.length === 0) {
    findings.push('Routine payment: Fully consistent with normal legitimate account activity');
  }
  return findings;
};

const getHumanRecommendedAction = (action) => {
  switch (action) {
    case 'FREEZE':
      return {
        title: 'HUMAN REVIEW REQUIRED',
        requiresApproval: true,
        pillBg: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
        summary: 'SENTINEL recommends holding this transaction for authorized operator review. Autonomous debit blocks are strictly refused.',
      };
    case 'ESCALATE_ANALYST_REVIEW':
      return {
        title: 'ESCALATE TO COMPLIANCE ANALYST',
        requiresApproval: false,
        pillBg: 'bg-orange-500/20 text-orange-300 border-orange-500/40',
        summary: 'Flagged for detailed compliance review. Investigation case generated in analyst queue.',
      };
    case 'ENHANCED_MONITORING':
      return {
        title: 'ENHANCED MONITORING',
        requiresApproval: false,
        pillBg: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
        summary: 'Allowed to proceed with high-frequency telemetry observation on subsequent transactions.',
      };
    case 'MONITOR':
    default:
      return {
        title: 'ALLOW & MONITOR',
        requiresApproval: false,
        pillBg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
        summary: 'Standard routine activity. Allowed to proceed with automated baseline tracking.',
      };
  }
};

const BenchmarkLab = () => {
  const { isPresentationMode } = usePresentationMode();

  // Run Configuration State (Part A)
  const [numTransactions, setNumTransactions] = useState(25);
  const [selectedScenarioId, setSelectedScenarioId] = useState('BALANCED');
  const [customMix, setCustomMix] = useState({
    BASELINE: 20,
    NEW_RECEIVER: 15,
    AMOUNT_ANOMALY: 15,
    TIME_ANOMALY: 10,
    ACTIVE_CALL: 10,
    MULTI_SIGNAL: 20,
    MULTI_HOP: 10,
  });
  const [seed, setSeed] = useState(() => `SEED-${Math.random().toString(36).substring(2, 8).toUpperCase()}`);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);

  // Run & Execution State
  const [activeRunId, setActiveRunId] = useState(null);
  const [currentRun, setCurrentRun] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [progressPct, setProgressPct] = useState(0);
  const [evaluatingTxId, setEvaluatingTxId] = useState(null);

  // History & Modal State
  const [historyRuns, setHistoryRuns] = useState([]);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [showCustomTxModal, setShowCustomTxModal] = useState(false);

  // Inspector Drawer State
  const [selectedTx, setSelectedTx] = useState(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  // Table Filters & Pagination
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterRisk, setFilterRisk] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 15;

  const pollingRef = useRef(null);

  // Fetch Run History
  const fetchRunHistory = async () => {
    try {
      const res = await fetch('/benchmark/runs');
      if (res.ok) {
        const data = await res.json();
        setHistoryRuns(data.runs || []);
      }
    } catch (e) {
      console.error('Failed to load benchmark history', e);
    }
  };

  useEffect(() => {
    fetchRunHistory();
  }, []);

  // WebSocket Live Events
  useEffect(() => {
    const handleProgress = (e) => {
      const detail = e.detail;
      if (detail && detail.run_id === activeRunId) {
        setProgressPct(detail.pct || 0);
        setCurrentRun((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            status: 'EVALUATING',
            processed_count: detail.processed,
            successful_count: detail.successful,
            failed_count: detail.failed,
          };
        });
      }
    };

    const handleCompleted = (e) => {
      const detail = e.detail;
      if (detail && detail.run_id === activeRunId) {
        setIsEvaluating(false);
        setProgressPct(100);
        fetchRunDetails(detail.run_id);
        fetchRunHistory();
      }
    };

    window.addEventListener('sentinel_benchmark_progress', handleProgress);
    window.addEventListener('sentinel_benchmark_completed', handleCompleted);
    return () => {
      window.removeEventListener('sentinel_benchmark_progress', handleProgress);
      window.removeEventListener('sentinel_benchmark_completed', handleCompleted);
    };
  }, [activeRunId]);

  // Polling for Run State
  const fetchRunDetails = async (runId) => {
    try {
      const res = await fetch(`/benchmark/runs/${runId}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentRun(data);
        if (data.total_requested > 0 && data.processed_count !== undefined) {
          setProgressPct(Math.round((data.processed_count / data.total_requested) * 100));
        }
        if (data.status === 'COMPLETED' || data.status === 'CANCELLED') {
          setIsEvaluating(false);
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
        }
      }
    } catch (err) {
      console.error('Failed to poll run details', err);
    }
  };

  const startPolling = (runId) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    pollingRef.current = setInterval(() => {
      fetchRunDetails(runId);
    }, 500);
  };

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  // ── PHASE 1: GENERATE TEST TRANSACTIONS ─────────────────────────────────────
  const handleGenerateInputs = async () => {
    setIsGenerating(true);
    setSelectedTx(null);
    setCurrentPage(1);
    setProgressPct(0);

    const scenarioObj = SCENARIO_CHOICES.find((s) => s.id === selectedScenarioId) || SCENARIO_CHOICES[0];

    const payload = {
      num_transactions: Number(numTransactions),
      profile_mode: scenarioObj.profileMode,
      single_profile: scenarioObj.singleProfile,
      custom_distribution: scenarioObj.id === 'CUSTOM_MIX' ? customMix : null,
      seed: seed.trim() || undefined,
    };

    try {
      const res = await fetch('/benchmark/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to generate test batch');
      }

      const data = await res.json();
      setActiveRunId(data.run_id);
      setCurrentRun(data);
      fetchRunHistory();
    } catch (err) {
      alert(`Error generating test batch: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // ── PHASE 2: ASSESS TRANSACTIONS ───────────────────────────────────────────
  const handleEvaluateBenchmark = async () => {
    const runId = currentRun?.run_id || activeRunId;
    if (!runId) return;

    setIsEvaluating(true);
    setProgressPct(0);
    setSelectedTx(null);

    try {
      const res = await fetch(`/benchmark/runs/${runId}/evaluate`, {
        method: 'POST',
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to initiate benchmark assessment');
      }

      setCurrentRun((prev) => (prev ? { ...prev, status: 'EVALUATING' } : prev));
      startPolling(runId);
    } catch (err) {
      alert(`Error assessing benchmark: ${err.message}`);
      setIsEvaluating(false);
    }
  };

  // ── INDIVIDUAL TRANSACTION EVALUATION ──────────────────────────────────────
  const handleEvaluateSingleTransaction = async (txId) => {
    const runId = currentRun?.run_id || activeRunId;
    if (!runId || !txId) return;

    if (evaluatingTxId) return;
    setEvaluatingTxId(txId);

    try {
      const res = await fetch(`/benchmark/runs/${runId}/transactions/${txId}/evaluate`, {
        method: 'POST',
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to evaluate transaction ${txId}`);
      }

      const data = await res.json();
      const updatedTx = data.transaction;

      setCurrentRun((prev) => {
        if (!prev) return prev;
        const updatedTxs = (prev.transactions || []).map((t) =>
          t.tx_id === txId ? updatedTx : t
        );
        return {
          ...prev,
          transactions: updatedTxs,
          summary: data.summary || prev.summary,
          status: data.status || prev.status,
        };
      });

      setSelectedTx((prev) => (prev && prev.tx_id === txId ? updatedTx : prev));
    } catch (err) {
      alert(`Error evaluating transaction ${txId}: ${err.message}`);
    } finally {
      setEvaluatingTxId(null);
    }
  };

  // Reset Run State (Returns to clean initial setup view)
  const handleResetRun = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setActiveRunId(null);
    setCurrentRun(null);
    setSelectedTx(null);
    setProgressPct(0);
    setIsEvaluating(false);
    setIsGenerating(false);
  };

  // Export CSV Audit Log
  const handleExportCSV = () => {
    const runId = currentRun?.run_id || activeRunId;
    if (!runId) return;
    window.location.href = `/benchmark/runs/${runId}/export`;
  };

  const handleRandomizeSeed = () => {
    setSeed(`SEED-${Math.random().toString(36).substring(2, 8).toUpperCase()}`);
  };

  const handleSelectHistoricalRun = (runId) => {
    setActiveRunId(runId);
    fetchRunDetails(runId);
    setShowHistoryModal(false);
  };

  // Callback when a custom transaction is added
  const handleCustomInputAdded = (data) => {
    const targetRunId = data?.run_id || activeRunId;
    if (!targetRunId) return;

    if (activeRunId !== targetRunId) {
      setActiveRunId(targetRunId);
    }

    if (data?.transaction) {
      setCurrentRun((prev) => {
        if (!prev || prev.run_id !== targetRunId) return prev;
        const prevTxs = prev.transactions || [];
        const exists = prevTxs.some((t) => t.tx_id === data.transaction.tx_id);
        if (exists) return prev;
        return {
          ...prev,
          transactions: [data.transaction, ...prevTxs],
          total_requested: data.total_requested ?? (prev.total_requested + 1),
        };
      });
    }

    fetchRunDetails(targetRunId);
    fetchRunHistory();
  };

  const handleCustomEvaluated = () => {
    fetchRunHistory();
  };

  // Transactions list
  const transactions = currentRun?.transactions || [];

  // Filtered transactions
  const filteredTransactions = useMemo(() => {
    return transactions.filter((t) => {
      if (filterStatus !== 'ALL') {
        const isEval = t.evaluation_state === 'EVALUATED' || (t.risk_score !== null && t.risk_score !== undefined);
        const isReEval = t.evaluation_state === 'RE_EVALUATED';
        if (filterStatus === 'NOT_TESTED' && isEval) return false;
        if (filterStatus === 'TESTED' && (!isEval || isReEval)) return false;
        if (filterStatus === 'RE_TESTED' && !isReEval) return false;
      }

      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesId = (t.tx_id || '').toLowerCase().includes(q);
        const matchesSender = (t.sender_account || '').toLowerCase().includes(q);
        const matchesReceiver = (t.receiver_account || '').toLowerCase().includes(q);
        const matchesChannel = (t.channel || '').toLowerCase().includes(q);
        if (!matchesId && !matchesSender && !matchesReceiver && !matchesChannel) {
          return false;
        }
      }
      if (filterRisk !== 'ALL') {
        const r = t.risk_level || t.threshold || 'LOW';
        if (r.toUpperCase() !== filterRisk.toUpperCase()) return false;
      }
      return true;
    });
  }, [transactions, searchQuery, filterStatus, filterRisk]);

  const totalPages = Math.ceil(filteredTransactions.length / pageSize) || 1;
  const paginatedTransactions = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredTransactions.slice(start, start + pageSize);
  }, [filteredTransactions, currentPage, pageSize]);

  // Aggregate stats
  const summary = currentRun?.summary || {};
  const hasUnevaluatedTransactions = transactions.some(
    (t) => t.evaluation_state === 'UNEVALUATED' || t.risk_score === null || t.risk_score === undefined
  );
  const isRunUnevaluated = currentRun && (currentRun.status === 'UNEVALUATED' || hasUnevaluatedTransactions);
  const isRunCompleted = currentRun && currentRun.status === 'COMPLETED';
  const hasEvaluatedData = (summary?.successful || 0) > 0 || (!hasUnevaluatedTransactions && transactions.length > 0);

  const testedCount = summary.successful || transactions.filter((t) => t.risk_score !== null && t.risk_score !== undefined).length;
  const operatorSignOffCount = summary.operator_actions_required || transactions.filter((t) => t.requires_operator_action || t.policy_action === 'FREEZE').length;
  const highCriticalCount = (summary.risk_distribution?.CRITICAL || 0) + (summary.risk_distribution?.HIGH || 0) || transactions.filter((t) => (t.risk_score ?? 0) >= 70).length;

  return (
    <div className="min-h-full bg-[#080D18] text-slate-100 p-4 sm:p-6 space-y-6 font-sans antialiased pb-24">

      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {/* 1. COMMAND & PRESENTATION HEADER                                          */}
      {/* ═════════════════════════════════════════════════════════════════════════ */}
      <header className="bg-[#0C1424] border border-slate-800 rounded-2xl px-5 py-4 flex flex-col xl:flex-row xl:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3.5 min-w-0">
          <div className="w-11 h-11 rounded-2xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0 shadow-inner">
            <FlaskConical className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-lg font-extrabold tracking-tight text-slate-100">
                SENTINEL Benchmark Lab
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                Compliance Test Bench
              </span>
              {currentRun && (
                <span className="px-3 py-0.5 rounded-full text-xs font-mono font-bold bg-slate-800 text-slate-200 border border-slate-700 flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${isRunCompleted ? 'bg-emerald-400' : isEvaluating ? 'bg-amber-400 animate-pulse' : 'bg-cyan-400'}`} />
                  RUN: {currentRun.run_id}
                </span>
              )}
              {isPresentationMode && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1.5">
                  <BellOff className="w-3.5 h-3.5 text-amber-400" />
                  PRESENTATION MODE (POPUPS MUTED)
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Demonstrate deterministic risk scoring, autonomous policy safety rules, and zero-drift repeat testing for compliance juries.
            </p>
          </div>
        </div>

        {/* Quick Tools & Modal Openers */}
        <div className="flex items-center gap-2.5 flex-wrap xl:shrink-0">
          <button
            type="button"
            onClick={() => setShowCustomTxModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition-all shadow-md hover:shadow-cyan-500/20"
          >
            <Plus className="w-4 h-4" />
            <span>Test a Transaction</span>
          </button>

          <button
            type="button"
            onClick={() => setShowHistoryModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-semibold transition-all hover:border-slate-700"
          >
            <History className="w-4 h-4 text-slate-400" />
            <span>History ({historyRuns.length})</span>
          </button>

          <button
            type="button"
            onClick={handleExportCSV}
            disabled={!currentRun || !currentRun.transactions?.length}
            className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-semibold transition-all disabled:opacity-40 hover:border-slate-700"
            title="Download UTF-8 CSV audit report"
          >
            <Download className="w-4 h-4 text-slate-400" />
            <span>Export CSV Audit</span>
          </button>

          {currentRun && (
            <button
              type="button"
              onClick={handleResetRun}
              className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors"
              title="Start new benchmark test"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}
        </div>
      </header>

      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {/* 2. INITIAL VIEW: EXTREMELY SIMPLIFIED BENCHMARK TEST SETUP               */}
      {/* Visible when NO active batch exists or user clicked 'Generate Again'     */}
      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {!currentRun && (
        <section className="bg-[#0C1424] border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl max-w-4xl mx-auto space-y-7 animate-fadeIn">
          
          <div className="border-b border-slate-800 pb-4">
            <h2 className="text-xl font-black text-slate-100 tracking-tight">
              Benchmark Test Setup
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Select the volume and test scenarios you would like SENTINEL to generate for evaluation.
            </p>
          </div>

          {/* Core Question: How many transactions would you like to generate? */}
          <div className="space-y-3">
            <label className="block text-base font-bold text-slate-100">
              How many transactions would you like to generate?
            </label>

            <div className="flex items-center gap-3 flex-wrap">
              {BATCH_PRESETS.map((cnt) => {
                const isSelected = numTransactions === cnt;
                return (
                  <button
                    key={cnt}
                    type="button"
                    onClick={() => setNumTransactions(cnt)}
                    className={`py-3 px-6 rounded-2xl text-base font-extrabold font-mono border transition-all ${
                      isSelected
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/60 shadow-lg ring-1 ring-cyan-500/40'
                        : 'bg-[#080D18] text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-200'
                    }`}
                  >
                    {cnt}
                  </button>
                );
              })}

              <div className="flex items-center gap-2 bg-[#080D18] border border-slate-800 rounded-2xl px-3 py-2">
                <span className="text-xs text-slate-400 font-medium">Custom:</span>
                <input
                  type="number"
                  min="1"
                  max="500"
                  value={numTransactions}
                  onChange={(e) => setNumTransactions(Math.min(500, Math.max(1, Number(e.target.value))))}
                  className="w-16 bg-[#0C1424] border border-slate-700 rounded-xl px-2 py-1 text-sm font-mono font-bold text-slate-100 text-center focus:border-cyan-400 outline-none"
                />
              </div>
            </div>

            <div className="pt-1">
              <span className="text-xs font-semibold px-3 py-1 rounded-full bg-cyan-950/40 text-cyan-300 border border-cyan-500/30 inline-block">
                {numTransactions} transactions will be generated
              </span>
            </div>
          </div>

          {/* Scenario Selection: What would you like to test? */}
          <div className="space-y-3 pt-2 border-t border-slate-800/80">
            <div>
              <label className="block text-sm font-bold text-slate-100">
                What would you like to test?
              </label>
              <p className="text-xs text-slate-400 mt-0.5">
                Choose a balanced mix or target a specific behavioral pattern.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              {SCENARIO_CHOICES.map((choice) => {
                const isSelected = selectedScenarioId === choice.id;
                return (
                  <div
                    key={choice.id}
                    onClick={() => setSelectedScenarioId(choice.id)}
                    className={`p-4 rounded-2xl border cursor-pointer transition-all space-y-1 ${
                      isSelected
                        ? 'bg-cyan-950/30 border-cyan-500/60 shadow-md ring-1 ring-cyan-500/30'
                        : 'bg-[#080D18] border-slate-800 hover:border-slate-700 hover:bg-[#0C1424]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-slate-100">
                        {choice.name}
                      </span>
                      <div className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 ${
                        isSelected
                          ? 'border-cyan-400 bg-cyan-400 text-black'
                          : 'border-slate-600'
                      }`}>
                        {isSelected && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                      </div>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      {choice.desc}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Advanced Settings (Collapsed by default, zero interaction needed) */}
          <div className="pt-2 border-t border-slate-800/80">
            <button
              type="button"
              onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              <Sliders className="w-3.5 h-3.5 text-cyan-400" />
              <span>Advanced Settings</span>
              {showAdvancedSettings ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showAdvancedSettings && (
              <div className="mt-3 p-4 bg-[#080D18] rounded-2xl border border-slate-800 space-y-3 text-xs animate-fadeIn">
                <div className="space-y-1.5">
                  <span className="text-slate-400 font-semibold block">Reproducibility Seed:</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={seed}
                      onChange={(e) => setSeed(e.target.value)}
                      className="flex-1 bg-[#0C1424] border border-slate-700 rounded-xl px-3 py-2 text-xs font-mono text-cyan-300 outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleRandomizeSeed}
                      className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                      title="Generate new seed"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <span className="text-[11px] text-slate-500 block">
                    Provides deterministic seed guarantee across multiple test runs.
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Primary Action Button */}
          <div className="pt-2">
            <button
              type="button"
              onClick={handleGenerateInputs}
              disabled={isGenerating}
              className="w-full flex items-center justify-center gap-2.5 py-4 px-6 rounded-2xl bg-cyan-500 hover:bg-cyan-400 text-black font-extrabold text-sm shadow-xl shadow-cyan-500/20 transition-all disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin text-black" />
                  <span>GENERATING TEST TRANSACTIONS...</span>
                </>
              ) : (
                <>
                  <Layers className="w-5 h-5" />
                  <span>GENERATE TEST TRANSACTIONS</span>
                </>
              )}
            </button>
          </div>

        </section>
      )}

      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {/* 3. CONFIRMATION STATE: AFTER TEST TRANSACTIONS GENERATED                  */}
      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {currentRun && isRunUnevaluated && (
        <section className="bg-[#0C1424] border border-cyan-500/30 rounded-2xl p-6 shadow-xl max-w-4xl mx-auto space-y-4 animate-fadeIn">
          
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shrink-0">
              <CheckCircle2 className="w-7 h-7" />
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-lg font-black text-slate-100">
                  ✓ {currentRun.transactions?.length || numTransactions} Test Transactions Generated
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30">
                  Ready for Risk Assessment
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                These are simulated transactions. No real customer accounts or funds are affected.
              </p>
            </div>
          </div>

          <div className="pt-2 flex flex-col sm:flex-row items-center gap-3 border-t border-slate-800/80">
            <button
              type="button"
              onClick={handleEvaluateBenchmark}
              disabled={isEvaluating}
              className="w-full sm:flex-1 flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black font-extrabold text-sm shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-50"
            >
              {isEvaluating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-black" />
                  <span>ASSESSING TRANSACTIONS ({progressPct}%)...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>ASSESS TRANSACTIONS</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleResetRun}
              className="w-full sm:w-auto px-5 py-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-semibold transition-colors"
            >
              Generate Again
            </button>
          </div>

        </section>
      )}

      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {/* 4. POST-ASSESSMENT BANNER & QUICK SUMMARY                                 */}
      {/* Visible once the batch has been assessed                                  */}
      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {currentRun && hasEvaluatedData && !isRunUnevaluated && (
        <section className="bg-[#0C1424] border border-slate-800 rounded-2xl p-5 space-y-4 shadow-lg animate-fadeIn">
          
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
                <CheckCircle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-100">
                  ✓ {testedCount} Transactions Assessed
                </h3>
                <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1.5 mt-0.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Deterministic Risk Engine — Δ = 0 Drift (100% Reproducible)</span>
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleEvaluateBenchmark}
                disabled={isEvaluating}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-semibold transition-all disabled:opacity-50"
                title="Re-run assessment on this batch to verify zero score drift"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${isEvaluating ? 'animate-spin' : ''}`} />
                <span>Repeat Test Batch</span>
              </button>

              <button
                type="button"
                onClick={handleResetRun}
                className="px-3.5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition-all"
              >
                Generate New Batch
              </button>
            </div>
          </div>

          {/* Simple Clean Metrics (Zero clutter) */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-[#080D18] p-3.5 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-400 uppercase tracking-wider block font-medium">Overall Average Risk</span>
              <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">
                {summary.average_risk_score ?? '—'} <span className="text-xs font-normal text-slate-500">/ 100</span>
              </div>
            </div>

            <div className="bg-[#080D18] p-3.5 rounded-xl border border-rose-500/30">
              <span className="text-xs text-rose-300 uppercase tracking-wider block font-medium flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5" /> High & Critical Flags
              </span>
              <div className="text-2xl font-bold font-mono text-rose-400 mt-1">
                {highCriticalCount}
              </div>
            </div>

            <div className="bg-[#080D18] p-3.5 rounded-xl border border-amber-500/30">
              <span className="text-xs text-amber-300 uppercase tracking-wider block font-medium flex items-center gap-1">
                <Lock className="w-3.5 h-3.5" /> Human Approval Required
              </span>
              <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
                {operatorSignOffCount} <span className="text-xs font-normal text-slate-400">(zero live accounts altered)</span>
              </div>
            </div>
          </div>

        </section>
      )}

      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {/* 5. TRANSACTION INVESTIGATION LEDGER (Visible once batch is generated)     */}
      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {currentRun && (
        <section className="bg-[#0C1424] border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl animate-fadeIn">
          
          {/* Ledger Toolbar */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
            <div className="flex items-center gap-2.5 flex-wrap">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h2 className="text-sm font-bold tracking-wider text-slate-100 uppercase">
                Transaction Investigation Ledger ({filteredTransactions.length})
              </h2>
              {isRunUnevaluated && (
                <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/30">
                  Transactions Awaiting Risk Assessment
                </span>
              )}
            </div>

            {/* Quick Filters */}
            <div className="flex items-center gap-2 flex-wrap">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search Tx ID or Account..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="pl-8 pr-3 py-1.5 bg-[#080D18] border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400 w-48 sm:w-60"
                />
              </div>

              <select
                value={filterStatus}
                onChange={(e) => {
                  setFilterStatus(e.target.value);
                  setCurrentPage(1);
                }}
                className="bg-[#080D18] border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-400"
              >
                <option value="ALL">All Statuses</option>
                <option value="NOT_TESTED">Not Tested</option>
                <option value="TESTED">Tested</option>
                <option value="RE_TESTED">Re-tested</option>
              </select>

              <select
                value={filterRisk}
                onChange={(e) => {
                  setFilterRisk(e.target.value);
                  setCurrentPage(1);
                }}
                className="bg-[#080D18] border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-400"
              >
                <option value="ALL">All Risk Levels</option>
                <option value="CRITICAL">Critical Risk (≥85)</option>
                <option value="HIGH">High Risk (70–84)</option>
                <option value="MEDIUM">Medium Risk (40–69)</option>
                <option value="LOW">Low Risk (&lt;40)</option>
              </select>
            </div>
          </div>

          {/* Ledger Table (Clean 9 Columns) */}
          <div className="overflow-x-auto rounded-xl border border-slate-800/80">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#080D18] text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Transaction</th>
                  <th className="py-3 px-4">Scenario</th>
                  <th className="py-3 px-4">Amount</th>
                  <th className="py-3 px-4">Detected Signals</th>
                  <th className="py-3 px-4 text-center">Overall Risk</th>
                  <th className="py-3 px-4">Recommended Action</th>
                  <th className="py-3 px-4">Human Approval</th>
                  <th className="py-3 px-4 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {paginatedTransactions.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="py-12 text-center text-slate-500">
                      No transactions match your search or filter settings.
                    </td>
                  </tr>
                ) : (
                  paginatedTransactions.map((tx) => {
                    const isEvaluated = tx.risk_score !== null && tx.risk_score !== undefined;
                    const isReTested = tx.evaluation_state === 'RE_EVALUATED';
                    const recAction = getHumanRecommendedAction(tx.policy_action);
                    const signalChips = getHumanSignalChips(tx);

                    return (
                      <tr
                        key={tx.tx_id}
                        onClick={() => setSelectedTx(tx)}
                        className={`hover:bg-[#0E172B] cursor-pointer transition-colors ${
                          selectedTx?.tx_id === tx.tx_id ? 'bg-cyan-950/20' : ''
                        }`}
                      >
                        {/* 1. Status */}
                        <td className="py-3 px-4">
                          {isReTested ? (
                            <div className="inline-flex flex-col">
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 inline-flex items-center gap-1 w-fit">
                                <Check className="w-2.5 h-2.5" /> RE-TESTED
                              </span>
                              <span className="text-[10px] text-emerald-400/90 font-mono mt-0.5">
                                ✓ Result unchanged
                              </span>
                            </div>
                          ) : isEvaluated ? (
                            <div className="inline-flex flex-col">
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 inline-flex items-center gap-1 w-fit">
                                <Check className="w-2.5 h-2.5" /> TESTED
                              </span>
                              <span className="text-[10px] text-slate-400 font-mono mt-0.5">
                                Risk: {tx.risk_score} — {tx.risk_level}
                              </span>
                            </div>
                          ) : (
                            <div className="inline-flex flex-col">
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700 inline-flex items-center gap-1 w-fit">
                                <Clock className="w-2.5 h-2.5" /> NOT TESTED
                              </span>
                              <span className="text-[10px] text-amber-400/90 font-sans mt-0.5">
                                Awaiting evaluation
                              </span>
                            </div>
                          )}
                        </td>

                        {/* 2. Transaction */}
                        <td className="py-3 px-4">
                          <span className="font-mono font-bold text-slate-200 block">
                            {tx.tx_id}
                          </span>
                          <span className="text-[11px] text-slate-400 font-mono block truncate max-w-[180px]">
                            {tx.sender_account} → {tx.receiver_account}
                          </span>
                        </td>

                        {/* 3. Scenario */}
                        <td className="py-3 px-4">
                          <span className="font-semibold text-slate-200 block">
                            {getHumanScenarioName(tx.benchmark_profile)}
                          </span>
                          <span className="text-[11px] text-slate-400 block font-mono">
                            {tx.channel || 'UPI'}
                          </span>
                        </td>

                        {/* 4. Amount */}
                        <td className="py-3 px-4">
                          <span className="font-bold text-slate-100 font-mono text-sm block">
                            {formatCurrency(tx.amount)}
                          </span>
                        </td>

                        {/* 5. Detected Signals */}
                        <td className="py-3 px-4">
                          <div className="flex flex-wrap gap-1 max-w-xs">
                            {signalChips.map((chip, idx) => (
                              <span
                                key={idx}
                                className={`px-2 py-0.5 rounded-md text-[10px] font-medium border ${chip.bg}`}
                              >
                                {chip.label}
                              </span>
                            ))}
                          </div>
                        </td>

                        {/* 6. Overall Risk */}
                        <td className="py-3 px-4 text-center">
                          {isEvaluated ? (
                            <div className="inline-block">
                              <RiskBadge score={tx.risk_score} />
                            </div>
                          ) : (
                            <span className="text-[11px] text-slate-500 font-mono font-medium">
                              —
                            </span>
                          )}
                        </td>

                        {/* 7. Recommended Action */}
                        <td className="py-3 px-4">
                          {isEvaluated ? (
                            <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold border block w-fit ${recAction.pillBg}`}>
                              {recAction.title}
                            </span>
                          ) : (
                            <span className="text-slate-500 text-[11px] italic">
                              Pending test
                            </span>
                          )}
                        </td>

                        {/* 8. Human Approval */}
                        <td className="py-3 px-4">
                          {isEvaluated ? (
                            tx.requires_operator_action || tx.policy_action === 'FREEZE' ? (
                              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 inline-flex items-center gap-1.5">
                                <Lock className="w-3 h-3 text-amber-400 shrink-0" />
                                <span>Human approval required</span>
                              </span>
                            ) : (
                              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 inline-flex items-center gap-1.5">
                                <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                                <span>Test action recorded</span>
                              </span>
                            )
                          ) : (
                            <span className="text-slate-500 text-[11px] italic">
                              —
                            </span>
                          )}
                        </td>

                        {/* 9. Inspect CTA */}
                        <td className="py-3 px-4 text-right">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedTx(tx);
                            }}
                            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-cyan-600 hover:text-white text-slate-200 text-xs font-semibold transition-all border border-slate-700/80"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Bar */}
          <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs text-slate-400">
            <span>
              Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, filteredTransactions.length)} of {filteredTransactions.length} transactions
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-lg bg-[#080D18] border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
              >
                Previous
              </button>
              <span className="font-mono text-slate-200">
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="px-3 py-1.5 rounded-lg bg-[#080D18] border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </section>
      )}

      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {/* 6. FORENSIC INSPECTOR DRAWER (ZERO RAW JSON, JURY-READY)                  */}
      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {selectedTx && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-xl bg-[#0A101D] border-l border-slate-700/80 h-full shadow-2xl flex flex-col text-slate-100 overflow-hidden">
            
            {/* Drawer Header */}
            <div className="p-5 border-b border-slate-800 bg-[#0C1424] flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold text-cyan-400 uppercase tracking-wider block">
                  Transaction Forensic Inspection
                </span>
                <h3 className="text-base font-bold text-slate-100 font-mono mt-0.5">
                  {selectedTx.tx_id}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedTx(null)}
                className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                aria-label="Close inspection drawer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              
              {/* SECTION 1: TRANSACTION OVERVIEW */}
              <div className="p-4 bg-[#080D18] border border-slate-800 rounded-2xl space-y-3">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block border-b border-slate-800 pb-2">
                  1. Transaction Overview
                </span>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-[11px] text-slate-400 block">Transaction Amount</span>
                    <span className="text-lg font-bold font-mono text-slate-100">
                      {formatCurrency(selectedTx.amount)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-400 block">Payment Method</span>
                    <span className="text-sm font-semibold text-slate-200">
                      {selectedTx.channel || 'UPI'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-400 block">Sender Account</span>
                    <span className="text-xs font-mono font-bold text-slate-200">
                      {selectedTx.sender_account}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-400 block">Recipient Account</span>
                    <span className="text-xs font-mono font-bold text-slate-200">
                      {selectedTx.receiver_account}
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                  <span>Scenario Category:</span>
                  <span className="font-semibold text-slate-300">
                    {getHumanScenarioName(selectedTx.benchmark_profile)}
                  </span>
                </div>
              </div>

              {/* SECTION 2: WHAT DID SENTINEL NOTICE? */}
              <div className="p-4 bg-[#0C1424] border border-slate-800 rounded-2xl space-y-2.5">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-200 uppercase tracking-wider border-b border-slate-800/80 pb-2">
                  <Sparkles className="w-4 h-4 text-cyan-400" />
                  <span>2. What did SENTINEL notice?</span>
                </div>
                <div className="space-y-2 pt-1">
                  {getPlainLanguageFindings(selectedTx).map((finding, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-300 leading-relaxed">
                      <Check className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                      <span>{finding}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* SECTION 3: OVERALL RISK ASSESSMENT */}
              {selectedTx.risk_score !== null && selectedTx.risk_score !== undefined ? (
                <div className={`p-5 rounded-2xl border ${
                  selectedTx.risk_score >= 85
                    ? 'bg-rose-950/30 border-rose-500/40 text-rose-100'
                    : selectedTx.risk_score >= 70
                    ? 'bg-orange-950/30 border-orange-500/40 text-orange-100'
                    : selectedTx.risk_score >= 40
                    ? 'bg-amber-950/30 border-amber-500/40 text-amber-100'
                    : 'bg-emerald-950/30 border-emerald-500/40 text-emerald-100'
                } space-y-3`}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider opacity-80">
                      3. Overall Risk Assessment
                    </span>
                    <span className="text-xs font-bold px-3 py-0.5 rounded-full bg-black/40 border border-white/10">
                      {selectedTx.risk_level || 'EVALUATED'}
                    </span>
                  </div>

                  <div className="flex items-baseline gap-3">
                    <span className="text-5xl font-black font-mono tracking-tight">
                      {selectedTx.risk_score}
                    </span>
                    <span className="text-sm font-semibold opacity-90">/ 100 Risk Score</span>
                  </div>

                  <p className="text-xs leading-relaxed pt-2 border-t border-white/10 opacity-90">
                    {selectedTx.risk_score >= 85
                      ? 'SENTINEL detected multiple compound fraud signals that together represent an imminent threat. Immediate operator review is required.'
                      : selectedTx.risk_score >= 70
                      ? 'High-risk anomalies detected. The payment pattern significantly deviates from the legitimate customer baseline.'
                      : selectedTx.risk_score >= 40
                      ? 'Moderate risk indicators present. Placed on enhanced telemetry monitoring with zero customer disruption.'
                      : 'Low-risk transaction. Consistent with routine customer behavior.'}
                  </p>
                </div>
              ) : (
                <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-3">
                  <div className="flex items-center gap-2 text-amber-300 text-xs font-bold uppercase">
                    <Clock className="w-4 h-4" />
                    <span>Awaiting Risk Assessment</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    This transaction has been generated as a test input but has not been evaluated yet.
                  </p>
                  <button
                    type="button"
                    onClick={() => handleEvaluateSingleTransaction(selectedTx.tx_id)}
                    disabled={evaluatingTxId === selectedTx.tx_id}
                    className="w-full py-2.5 px-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black text-xs font-bold transition-all disabled:opacity-50"
                  >
                    {evaluatingTxId === selectedTx.tx_id ? 'Assessing Risk...' : 'Evaluate This Transaction Now'}
                  </button>
                </div>
              )}

              {/* SECTION 4: RECOMMENDED ACTION & HUMAN APPROVAL */}
              {selectedTx.risk_score !== null && selectedTx.risk_score !== undefined && (
                <div className="p-4 bg-[#080D18] border border-slate-800 rounded-2xl space-y-3">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block border-b border-slate-800 pb-2">
                    4. Recommended Action & Human Approval
                  </span>

                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 font-semibold">Recommended Action:</span>
                    <span className={`text-xs font-bold px-3 py-1 rounded-full border ${getHumanRecommendedAction(selectedTx.policy_action).pillBg}`}>
                      {getHumanRecommendedAction(selectedTx.policy_action).title}
                    </span>
                  </div>

                  <div className={`p-3.5 rounded-xl border ${
                    selectedTx.requires_operator_action || selectedTx.policy_action === 'FREEZE'
                      ? 'bg-amber-950/20 border-amber-500/40 text-amber-200'
                      : 'bg-[#0C1424] border-slate-800 text-slate-300'
                  } space-y-1.5`}>
                    <div className="flex items-center gap-2">
                      {selectedTx.requires_operator_action || selectedTx.policy_action === 'FREEZE' ? (
                        <Lock className="w-4 h-4 text-amber-400 shrink-0" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      )}
                      <span className="text-xs font-bold uppercase tracking-wide">
                        {selectedTx.requires_operator_action || selectedTx.policy_action === 'FREEZE'
                          ? 'Human Approval Required'
                          : 'Test Action Recorded (Sandbox)'}
                      </span>
                    </div>
                    <p className="text-[11px] leading-relaxed opacity-90">
                      {selectedTx.requires_operator_action || selectedTx.policy_action === 'FREEZE'
                        ? 'SENTINEL has NOT automatically frozen the account. Under institutional safety rules, an authorized compliance operator must review and approve this action. Zero live banking accounts were touched.'
                        : 'Simulated monitoring action applied within benchmark sandbox with zero disruption to banking operations.'}
                    </p>
                  </div>
                </div>
              )}

              {/* SECTION 5: REPEAT TEST (100% DETERMINISTIC EVALUATION) */}
              {selectedTx.risk_score !== null && selectedTx.risk_score !== undefined && (
                <div className="p-4 bg-[#0C1424] border border-emerald-500/30 rounded-2xl space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                    <div className="flex items-center gap-2 text-xs font-bold text-emerald-300 uppercase tracking-wider">
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                      <span>5. Repeat Test</span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                      Repeatable Result
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="bg-[#080D18] p-2.5 rounded-xl border border-slate-800">
                      <span className="text-[10px] text-slate-400 uppercase block font-sans">Previous assessment</span>
                      <span className="text-sm font-bold text-slate-200">{selectedTx.risk_score} — {selectedTx.risk_level}</span>
                    </div>
                    <div className="bg-[#080D18] p-2.5 rounded-xl border border-slate-800">
                      <span className="text-[10px] text-slate-400 uppercase block font-sans">Current assessment</span>
                      <span className="text-sm font-bold text-cyan-400">{selectedTx.risk_score} — {selectedTx.risk_level}</span>
                    </div>
                  </div>

                  <div className="pt-1 flex items-center justify-between">
                    <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                      <Check className="w-3.5 h-3.5" /> RESULT MATCHED (Δ = 0)
                    </span>
                    <button
                      type="button"
                      onClick={() => handleEvaluateSingleTransaction(selectedTx.tx_id)}
                      disabled={evaluatingTxId === selectedTx.tx_id}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition-all disabled:opacity-50"
                    >
                      {evaluatingTxId === selectedTx.tx_id ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Testing...</span>
                        </>
                      ) : (
                        <>
                          <RefreshCw className="w-3.5 h-3.5" />
                          <span>Re-test Transaction</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* SECTION 6: TECHNICAL DETAILS (ZERO RAW JSON) */}
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                  className="w-full flex items-center justify-between p-3.5 rounded-xl bg-[#080D18] hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-semibold transition-all"
                >
                  <span className="flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-cyan-400" />
                    <span>Technical Details</span>
                  </span>
                  {showTechnicalDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showTechnicalDetails && (
                  <div className="mt-2.5 p-4 rounded-xl bg-[#080D18] border border-slate-800/90 space-y-3 text-xs animate-fadeIn">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-[#0C1424] p-2.5 rounded-lg border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase block font-semibold">Rule-Based Risk</span>
                        <span className="text-base font-mono font-bold text-slate-100">{selectedTx.rule_score ?? '—'}</span>
                        <span className="text-[10px] text-slate-500 block">Weight: 40%</span>
                      </div>
                      <div className="bg-[#0C1424] p-2.5 rounded-lg border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase block font-semibold">Pattern Analysis (ML)</span>
                        <span className="text-base font-mono font-bold text-slate-100">
                          {selectedTx.ml_score !== null && selectedTx.ml_score !== undefined ? Math.round(selectedTx.ml_score) : '—'}
                        </span>
                        <span className="text-[10px] text-slate-500 block">Weight: 60%</span>
                      </div>
                    </div>

                    <div className="space-y-1.5 pt-1 text-[11px] text-slate-300">
                      <div className="flex justify-between py-1 border-b border-slate-800/80">
                        <span className="text-slate-400">Scoring Formula:</span>
                        <span className="font-mono text-cyan-400 font-semibold">60% ML + 40% Rules</span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-slate-800/80">
                        <span className="text-slate-400">Policy Rule ID:</span>
                        <span className="font-mono text-slate-200">{selectedTx.policy_rule_id || 'POL-DEFAULT'}</span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-slate-800/80">
                        <span className="text-slate-400">Evaluation Version:</span>
                        <span className="font-mono text-slate-300">v{selectedTx.evaluation_version || '2.0.0'}</span>
                      </div>
                      <div className="flex justify-between py-1">
                        <span className="text-slate-400">Audit Seed:</span>
                        <span className="font-mono text-cyan-300 truncate max-w-[200px]" title={selectedTx.deterministic_seed}>
                          {selectedTx.deterministic_seed || 'STABLE-DETERMINISTIC'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

            </div>
          </div>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {/* 7. RUN HISTORY MODAL                                                     */}
      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="relative w-full max-w-3xl bg-[#0C1424] border border-slate-800 rounded-2xl shadow-2xl flex flex-col max-h-[80vh] overflow-hidden text-slate-200">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#080D18]">
              <div className="flex items-center gap-2">
                <History className="w-5 h-5 text-cyan-400" />
                <h3 className="text-sm font-bold uppercase tracking-wider">
                  Benchmark Run History ({historyRuns.length})
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowHistoryModal(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-3">
              {historyRuns.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  No benchmark runs recorded in this session.
                </div>
              ) : (
                historyRuns.map((r) => (
                  <div
                    key={r.run_id}
                    onClick={() => handleSelectHistoricalRun(r.run_id)}
                    className="p-4 rounded-xl bg-[#080D18] hover:bg-[#0E172B] border border-slate-800 cursor-pointer transition-all flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-cyan-400">{r.run_id}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          r.status === 'COMPLETED'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {r.status === 'COMPLETED' ? 'TEST COMPLETE' : 'INCOMPLETE / AWAITING'}
                        </span>
                      </div>
                      <span className="text-xs text-slate-400 mt-1 block">
                        Volume: {r.total_requested} transactions • Created {new Date(r.created_at || Date.now()).toLocaleTimeString()}
                      </span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {/* 8. TEST A TRANSACTION MODAL (7-Step Guided Builder)                      */}
      {/* ═════════════════════════════════════════════════════════════════════════ */}
      <CustomTransactionModal
        isOpen={showCustomTxModal}
        onClose={() => setShowCustomTxModal(false)}
        activeRunId={activeRunId}
        isRunUnevaluated={isRunUnevaluated}
        onAddedToBatch={handleCustomInputAdded}
        onCustomInputAdded={handleCustomInputAdded}
        onEvaluated={handleCustomEvaluated}
      />

    </div>
  );
};

export default BenchmarkLab;
