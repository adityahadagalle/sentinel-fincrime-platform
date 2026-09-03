import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { 
  Shield, Activity, ShieldAlert, TrendingUp, CheckCircle2, Zap, 
  BarChart3, PieChart as PieIcon, Layers, Network, DollarSign, Server, 
  RefreshCw, Clock, Filter, ArrowUpRight, ArrowDownRight, UserCheck, Lock, FileText, AlertTriangle,
  Play, Pause, RotateCcw, X, Eye, ChevronRight
} from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, AreaChart, Area, BarChart, Bar, ReferenceLine
} from 'recharts';
import RiskScoreTrend from '../components/RiskScoreTrend';

const Dashboard = () => {
  const { transactions, cases, actions, connectionStatus } = useWebSocket();
  const [timeframe, setTimeframe] = useState('30d');
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Real-time Risk Score Trend chart state
  const [isChartLive, setIsChartLive] = useState(true);
  const [windowSize, setWindowSize] = useState(30);
  const [chartBufferQueue, setChartBufferQueue] = useState([]);
  const [selectedChartPoint, setSelectedChartPoint] = useState(null);
  const [liveTrendWindow, setLiveTrendWindow] = useState([]);

  // Fetch analytics overview telemetry
  const fetchAnalytics = useCallback(async () => {
    try {
      let res;
      try {
        res = await fetch(`/analytics/overview?timeframe=${timeframe}`);
      } catch {
        res = await fetch(`http://localhost:8000/analytics/overview?timeframe=${timeframe}`);
      }
      if (res.ok) {
        const data = await res.json();
        setAnalyticsData(data);
      }
    } catch (err) {
      console.error('Failed to fetch analytics overview:', err);
    } finally {
      setLoading(false);
    }
  }, [timeframe]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  useEffect(() => {
    const interval = setInterval(fetchAnalytics, 10000);
    return () => clearInterval(interval);
  }, [fetchAnalytics]);

  // Sync real-time transactions into liveTrendWindow
  useEffect(() => {
    if (!transactions || transactions.length === 0) return;

    if (!isChartLive) {
      // Buffer new transactions when chart is paused
      const newestTx = transactions[0];
      setChartBufferQueue(prev => {
        if (prev.some(t => t.tx_id === newestTx.tx_id)) return prev;
        return [newestTx, ...prev];
      });
      return;
    }

    // Form live trend stream from deduplicated transactions
    const sortedTxs = [...transactions].reverse();
    const formatted = sortedTxs.map((tx) => {
      const score = Number(tx.risk_score || 0);
      const timestampLabel = String(tx.timestamp || '').slice(11, 19) || 'Just now';
      return {
        tx_id: tx.tx_id,
        timestamp: timestampLabel,
        score: score,
        rawTx: tx,
        risk_level: score >= 85 ? 'CRITICAL' : score >= 70 ? 'HIGH' : score >= 40 ? 'MEDIUM' : 'LOW'
      };
    });

    setLiveTrendWindow(formatted.slice(-windowSize));
  }, [transactions, isChartLive, windowSize]);

  // Handle Resume LIVE chart mode
  const handleResumeLive = () => {
    setIsChartLive(true);
    setChartBufferQueue([]);
  };

  // Metrics derived from liveTrendWindow
  const liveMetrics = useMemo(() => {
    if (liveTrendWindow.length === 0) {
      return { currentRisk: 0, avgRisk: 0, highRiskCount: 0, critRiskCount: 0, latestTx: null };
    }
    const latest = liveTrendWindow[liveTrendWindow.length - 1];
    const totalScore = liveTrendWindow.reduce((acc, curr) => acc + curr.score, 0);
    const avgRisk = Math.round(totalScore / liveTrendWindow.length);
    const highRiskCount = liveTrendWindow.filter(t => t.score >= 70 && t.score < 85).length;
    const critRiskCount = liveTrendWindow.filter(t => t.score >= 85).length;

    return {
      currentRisk: latest.score,
      avgRisk,
      highRiskCount,
      critRiskCount,
      latestTx: latest.rawTx
    };
  }, [liveTrendWindow]);





  // Recent 5 Risk Events
  const recentRiskEvents = useMemo(() => {
    return [...liveTrendWindow].reverse().slice(0, 5);
  }, [liveTrendWindow]);

  const kpis = analyticsData?.kpis || {
    total_transactions: transactions.length || 12842,
    total_transactions_trend: "+12.4%",
    risk_alerts: transactions.filter(t => t.risk_score >= 40).length || 1842,
    risk_alerts_trend: "+24.0%",
    avg_risk_score: transactions.length 
      ? Math.round(transactions.reduce((acc, t) => acc + (t.risk_score || 0), 0) / transactions.length) 
      : 68,
    avg_risk_score_trend: "-2.1%",
    cases_resolved: cases.filter(c => c.status === 'ACTIONED' || c.status === 'CLOSED').length || 432,
    cases_resolved_trend: "+16.0%"
  };

  const alertsByRiskLevel = analyticsData?.alerts_by_risk_level || [
    { name: 'CRITICAL', value: 142, color: '#ef4444', percentage: 11.5 },
    { name: 'HIGH', value: 384, color: '#f59e0b', percentage: 31.2 },
    { name: 'MEDIUM', value: 512, color: '#38bdf8', percentage: 41.6 },

    { name: 'LOW', value: 194, color: '#10b981', percentage: 15.7 }
  ];

  const investigationPerf = analyticsData?.investigation_performance || {
    cases_opened: cases.length || 580,
    cases_investigated: cases.length || 580,
    cases_resolved: cases.filter(c => c.status === 'ACTIONED' || c.status === 'CLOSED').length || 432,
    cases_escalated: cases.filter(c => c.status === 'HIGH_RISK').length || 88,
    resolution_rate: 78.4,
    avg_investigation_time: "1h 42m"
  };

  const actionOutcomes = analyticsData?.action_outcomes || [
    { action: 'MONITOR', count: 420 },
    { action: 'ENHANCED MONITORING', count: 310 },
    { action: 'ESCALATE', count: 180 },
    { action: 'BLOCK', count: 95 },
    { action: 'REJECT', count: 64 },
    { action: 'FREEZE', count: 42 },
    { action: 'FILE STR', count: 28 },
    { action: 'CLOSE ACCOUNT', count: 18 }
  ];

  const autoIntel = analyticsData?.automation_intelligence || {
    automation_mode: true,
    automated_actions_count: actions.filter(a => a.actor_type === 'AUTOMATION_ENGINE').length || 850,
    human_actions_count: actions.filter(a => a.actor_type === 'HUMAN_OPERATOR').length || 290,
    automation_rate: 74.5,
    operator_interventions_count: 290,
    freeze_interventions_count: 42
  };

  const channelPerf = analyticsData?.channel_performance || [
    { channel: 'UPI', tx_count: 6420, total_amount: 28500000, risk_rate: 8.4 },
    { channel: 'IMPS', tx_count: 3120, total_amount: 42000000, risk_rate: 12.1 },
    { channel: 'NEFT', tx_count: 1840, total_amount: 89000000, risk_rate: 6.2 },
    { channel: 'CARD', tx_count: 980, total_amount: 14500000, risk_rate: 14.8 },
    { channel: 'NET BANKING', tx_count: 480, total_amount: 38000000, risk_rate: 9.3 }
  ];

  const patterns = analyticsData?.detected_patterns || [
    { pattern: "New Receiver", occurrences: 428, risk_contribution: "Medium" },
    { pattern: "High Transaction Amount", occurrences: 312, risk_contribution: "High" },
    { pattern: "Cross-Border Activity", occurrences: 194, risk_contribution: "Critical" },
    { pattern: "Multi-Hop Mule Chain", occurrences: 126, risk_contribution: "Critical" },
    { pattern: "Funnel Account", occurrences: 88, risk_contribution: "High" },
    { pattern: "Circular Flow", occurrences: 44, risk_contribution: "Critical" }
  ];

  const netIntel = analyticsData?.network_intelligence || {
    avg_hops: 4.2,
    max_hops: 8,
    multihop_cases: 126,
    mule_networks: 34,
    circular_flows: 18,
    shared_intermediaries: 22
  };

  const finImpact = analyticsData?.financial_impact || {
    total_exposure: 18400000.0,
    recovered_assets: 14200000.0,
    in_flight: 2800000.0,
    estimated_loss: 1400000.0,
    recovery_rate: 77.2
  };

  const sysHealth = analyticsData?.system_health || {
    pipeline: "Operational",
    database: "Operational",
    websocket: "Operational",
    risk_engine: "Operational",
    policy_engine: "Operational",
    automation_engine: "Operational"
  };

  // Custom Dot Renderer for Risk Score Trend Chart (SENTINEL Blue Theme)
  const renderCustomDot = (props) => {
    const { cx, cy, payload, index } = props;
    if (!cx || !cy) return null;

    const isLatest = index === liveTrendWindow.length - 1;

    return (
      <g key={`dot-${index}`}>
        {isLatest && (
          <circle cx={cx} cy={cy} r={11} fill="#38bdf8" fillOpacity={0.4} className="animate-ping" />
        )}
        <circle 
          cx={cx} 
          cy={cy} 
          r={isLatest ? 5.5 : 3.5} 
          fill="#38bdf8" 
          stroke="#0f172a" 
          strokeWidth={2} 
          style={{ cursor: 'pointer' }}
          onClick={() => setSelectedChartPoint(payload)}
        />
      </g>
    );
  };



  return (
    <div className="p-6 md:p-8 bg-slate-950 min-h-screen text-slate-100 font-sans space-y-8 select-none">
      
      {/* ── HEADER ────────────────────────────────────────────────────────────── */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-100 font-mono uppercase">
                Analytics Overview
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Financial crime intelligence, risk trends and investigation performance
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="inline-flex p-1 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono">
            {[
              { label: '24 Hours', value: '24h' },
              { label: '7 Days', value: '7d' },
              { label: '30 Days', value: '30d' },
              { label: '12 Months', value: '12m' }
            ].map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setTimeframe(item.value)}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  timeframe === item.value
                    ? 'bg-sky-600 text-white shadow-md shadow-sky-950/60'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={fetchAnalytics}
            title="Refresh Telemetry Data"
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          </button>
        </div>
      </header>

      {/* ── TIER 1: PRIMARY KPI CARDS ───────────────────────────────────────── */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        
        {/* Card 1: Total Transactions */}
        <div className="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl flex flex-col justify-between hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
              Total Transactions
            </span>
            <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="flex items-baseline justify-between">
              <span className="text-3xl font-mono font-extrabold text-slate-100">
                {kpis.total_transactions.toLocaleString()}
              </span>
              <span className="inline-flex items-center gap-0.5 text-xs font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-600/40">
                <ArrowUpRight className="w-3 h-3" />
                {kpis.total_transactions_trend}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1 font-mono">Processed this period</p>
          </div>
        </div>

        {/* Card 2: Risk Alerts */}
        <div className="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl flex flex-col justify-between hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
              Risk Alerts
            </span>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="flex items-baseline justify-between">
              <span className="text-3xl font-mono font-extrabold text-slate-100">
                {kpis.risk_alerts.toLocaleString()}
              </span>
              <span className="inline-flex items-center gap-0.5 text-xs font-mono font-bold text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-600/40">
                <ArrowUpRight className="w-3 h-3" />
                {kpis.risk_alerts_trend}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1 font-mono">Alerts generated</p>
          </div>
        </div>

        {/* Card 3: Average Risk Score */}
        <div className="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl flex flex-col justify-between hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
              Average Risk Score
            </span>
            <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="flex items-baseline justify-between">
              <span className="text-3xl font-mono font-extrabold text-slate-100">
                {kpis.avg_risk_score}
              </span>
              <span className="inline-flex items-center gap-0.5 text-xs font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-600/40">
                <ArrowDownRight className="w-3 h-3" />
                {kpis.avg_risk_score_trend}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1 font-mono">System average</p>
          </div>
        </div>

        {/* Card 4: Cases Resolved */}
        <div className="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl flex flex-col justify-between hover:border-slate-700/80 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
              Cases Resolved
            </span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="flex items-baseline justify-between">
              <span className="text-3xl font-mono font-extrabold text-slate-100">
                {kpis.cases_resolved.toLocaleString()}
              </span>
              <span className="inline-flex items-center gap-0.5 text-xs font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-600/40">
                <ArrowUpRight className="w-3 h-3" />
                {kpis.cases_resolved_trend}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1 font-mono">Resolved this period</p>
          </div>
        </div>

      </section>

      {/* ── TIER 2: TRUE REAL-TIME LIVE RISK SCORE TREND & ALERTS ───────────── */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Real-Time Risk Score Trend Line Chart (2/3 width) */}
        <div className="lg:col-span-2">
          <RiskScoreTrend
            transactions={transactions}
            connectionStatus={connectionStatus}
            onSelectTransaction={(tx) => setSelectedAuditTx(tx)}
          />
        </div>

        {/* Alerts by Risk Level Donut Chart (1/3 width) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-amber-400" />
              Alerts by Risk Level
            </h3>
            <p className="text-[11px] text-slate-400 font-sans mt-0.5">
              Distribution of incoming transaction risk classifications
            </p>
          </div>

          <div className="h-[220px] w-full relative flex items-center justify-center my-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={alertsByRiskLevel}
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {alertsByRiskLevel.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', color: '#f8fafc' }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-mono font-extrabold text-slate-100">
                {alertsByRiskLevel.reduce((acc, curr) => acc + curr.value, 0)}
              </span>
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Total Alerts</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80">
            {alertsByRiskLevel.map((item) => (
              <div key={item.name} className="flex items-center justify-between text-xs font-mono p-1.5 rounded bg-slate-950/60 border border-slate-800/60">
                <span className="flex items-center gap-1.5 font-bold text-slate-300">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                  {item.name}
                </span>
                <span className="font-semibold text-slate-400">{item.percentage}%</span>
              </div>
            ))}
          </div>
        </div>

      </section>

      {/* ── TIER 3: INVESTIGATION PERFORMANCE, ACTION OUTCOMES, AUTOMATION INTEL ── */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Card 1: Investigation Performance */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
              <Clock className="w-4 h-4 text-emerald-400" />
              Investigation Performance
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-600/60 font-bold">
              {investigationPerf.resolution_rate}% Resolved
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Cases Opened</span>
              <span className="text-xl font-mono font-bold text-slate-100">{investigationPerf.cases_opened}</span>
            </div>
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Cases Resolved</span>
              <span className="text-xl font-mono font-bold text-emerald-400">{investigationPerf.cases_resolved}</span>
            </div>
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Cases Escalated</span>
              <span className="text-xl font-mono font-bold text-amber-400">{investigationPerf.cases_escalated}</span>
            </div>
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Avg Invest. Time</span>
              <span className="text-base font-mono font-bold text-sky-400">{investigationPerf.avg_investigation_time}</span>
            </div>
          </div>
        </div>

        {/* Card 2: Action Outcomes */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-purple-400" />
              Action Outcomes
            </h3>
            <span className="text-[10px] font-mono text-slate-400">Total: {actionOutcomes.reduce((acc, curr) => acc + curr.count, 0)}</span>
          </div>

          <div className="space-y-2 pt-1 max-h-[220px] overflow-y-auto pr-1">
            {actionOutcomes.map((item) => (
              <div key={item.action} className="space-y-1">
                <div className="flex justify-between text-[11px] font-mono">
                  <span className="text-slate-300 font-bold">{item.action}</span>
                  <span className="text-slate-400">{item.count}</span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                  <div 
                    className="bg-purple-500 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${Math.min(100, (item.count / 450) * 100)}%` }} 
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Card 3: Automation Intelligence */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400 animate-pulse" />
              Automation Intelligence
            </h3>
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
              autoIntel.automation_mode 
                ? 'bg-emerald-950 text-emerald-300 border-emerald-600/60' 
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              {autoIntel.automation_mode ? 'ACTIVE' : 'OFF'}
            </span>
          </div>

          <div className="space-y-3 pt-1">
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 flex justify-between items-center">
              <span className="text-xs font-mono text-slate-300 font-medium">Automated Actions</span>
              <span className="text-base font-mono font-bold text-emerald-400">{autoIntel.automated_actions_count}</span>
            </div>
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 flex justify-between items-center">
              <span className="text-xs font-mono text-slate-300 font-medium">Human Operator Actions</span>
              <span className="text-base font-mono font-bold text-purple-400">{autoIntel.human_actions_count}</span>
            </div>
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 flex justify-between items-center">
              <span className="text-xs font-mono text-slate-300 font-medium">Automation Rate</span>
              <span className="text-base font-mono font-bold text-amber-400">{autoIntel.automation_rate}%</span>
            </div>
          </div>
        </div>

      </section>

      {/* ── TIER 4: CHANNEL PERFORMANCE, DETECTED PATTERNS, NETWORK INTEL ──── */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Channel Performance (1/3) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <Layers className="w-4 h-4 text-sky-400" />
            Channel Performance
          </h3>

          <div className="space-y-2.5 pt-1">
            {channelPerf.map((ch) => (
              <div key={ch.channel} className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/80 flex items-center justify-between text-xs font-mono">
                <div>
                  <span className="text-sky-300 font-bold block">{ch.channel}</span>
                  <span className="text-[10px] text-slate-500">{ch.tx_count.toLocaleString()} txs</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-200 font-bold block">₹{(ch.total_amount / 1000000).toFixed(1)}M</span>
                  <span className={`text-[10px] font-bold ${ch.risk_rate >= 10 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    Risk {ch.risk_rate}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Detected Patterns (1/3) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Detected AML Patterns
          </h3>

          <div className="space-y-2 pt-1 max-h-[260px] overflow-y-auto pr-1">
            {patterns.map((p) => (
              <div key={p.pattern} className="p-2.5 bg-slate-950/80 rounded-xl border border-slate-800 flex items-center justify-between text-xs font-mono">
                <div>
                  <span className="text-slate-200 font-bold block">{p.pattern}</span>
                  <span className="text-[10px] text-slate-500">{p.occurrences} detections</span>
                </div>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                  p.risk_contribution === 'Critical' ? 'bg-rose-950 text-rose-300 border-rose-600/60' :
                  p.risk_contribution === 'High' ? 'bg-amber-950 text-amber-300 border-amber-600/60' :
                  'bg-sky-950 text-sky-300 border-sky-600/60'
                }`}>
                  {p.risk_contribution}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Network Intelligence (Multi-Hop) (1/3) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <Network className="w-4 h-4 text-indigo-400" />
            Network Intelligence (Multi-Hop)
          </h3>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Avg Path</span>
              <span className="text-xl font-mono font-bold text-sky-400">{netIntel.avg_hops} hops</span>
            </div>
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Max Path</span>
              <span className="text-xl font-mono font-bold text-purple-400">{netIntel.max_hops} hops</span>
            </div>
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Mule Networks</span>
              <span className="text-xl font-mono font-bold text-amber-400">{netIntel.mule_networks}</span>
            </div>
            <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 block">Circular Flows</span>
              <span className="text-xl font-mono font-bold text-rose-400">{netIntel.circular_flows}</span>
            </div>
          </div>
        </div>

      </section>

      {/* ── TIER 5: FINANCIAL IMPACT & SYSTEM HEALTH TELEMETRY ──────────────── */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-4">
        
        {/* Financial Impact & Asset Recovery (2/3) */}
        <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-emerald-400" />
              Financial Exposure & Recovery Telemetry
            </h3>
            <span className="text-[10px] font-mono text-emerald-400 font-bold px-2 py-0.5 rounded bg-emerald-950 border border-emerald-600/60">
              Recovery Rate: {finImpact.recovery_rate}%
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-1">
            <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Total Exposure</span>
              <span className="text-lg font-mono font-extrabold text-slate-100 mt-1 block">
                ₹{(finImpact.total_exposure / 100000).toFixed(1)}L
              </span>
            </div>
            <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Recovered Assets</span>
              <span className="text-lg font-mono font-extrabold text-emerald-400 mt-1 block">
                ₹{(finImpact.recovered_assets / 100000).toFixed(1)}L
              </span>
            </div>
            <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">In Flight / Frozen</span>
              <span className="text-lg font-mono font-extrabold text-sky-400 mt-1 block">
                ₹{(finImpact.in_flight / 100000).toFixed(1)}L
              </span>
            </div>
            <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Estimated Loss</span>
              <span className="text-lg font-mono font-extrabold text-rose-400 mt-1 block">
                ₹{(finImpact.estimated_loss / 100000).toFixed(1)}L
              </span>
            </div>
          </div>
        </div>

        {/* System Health Telemetry (1/3) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <Server className="w-4 h-4 text-sky-400" />
            System Health Telemetry
          </h3>

          <div className="grid grid-cols-2 gap-2.5 pt-1 text-xs font-mono">
            {Object.entries(sysHealth).map(([key, status]) => (
              <div key={key} className="p-2.5 bg-slate-950/80 rounded-xl border border-slate-800 flex flex-col gap-1">
                <span className="text-[10px] text-slate-500 uppercase font-bold">{key.replace('_', ' ')}</span>
                <span className="flex items-center gap-1.5 text-[11px] font-bold text-emerald-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  {status}
                </span>
              </div>
            ))}
          </div>
        </div>

      </section>

      {/* ── FOOTER ────────────────────────────────────────────────────────────── */}
      <footer className="pt-6 pb-4 border-t border-slate-800/80 flex flex-col sm:flex-row justify-between items-center gap-3 text-xs text-slate-500 font-mono">
        <span>SENTINEL Financial Crime Intelligence Platform • Analytics Engine</span>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-emerald-400">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping" />
            Real-time Telemetry Live
          </span>
        </div>
      </footer>

    </div>
  );
};

export default Dashboard;
