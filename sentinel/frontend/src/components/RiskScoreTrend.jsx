import React, { useState, useEffect, useMemo } from 'react';
import { TrendingUp, Pause, Play, Activity } from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

/**
 * SENTINEL Risk Score Trend
 *
 * Replicates the reference Sentinel design language:
 * - Clean dark aesthetic (#070D1A, border #1A2640)
 * - LIVE indicator with pulsing dot & PAUSE/RESUME controls
 * - Rolling window selector: 10TX, 20TX, 30TX, 50TX
 * - 4-metric summary ribbon: CURRENT RISK, AVG RISK, HIGH RISK, CRITICAL
 * - Sleek AreaChart with deep solid blue gradient (#1E40AF -> #0A1B3A), no clutter dots
 * - Recent Stream Risk Events interactive chips
 */
const RiskScoreTrend = ({ transactions = [], connectionStatus = 'LIVE', onSelectTransaction }) => {
  const [isLive, setIsLive] = useState(true);
  const [windowSize, setWindowSize] = useState(30);
  const [bufferQueue, setBufferQueue] = useState([]);
  const [liveData, setLiveData] = useState([]);
  const [selectedPoint, setSelectedPoint] = useState(null);

  // Sync real-time incoming transactions into rolling window
  useEffect(() => {
    if (!transactions || transactions.length === 0) return;

    if (!isLive) {
      // Buffer latest arrivals when paused
      const latest = transactions[0];
      setBufferQueue((prev) => {
        if (prev.some((t) => t.tx_id === latest.tx_id)) return prev;
        return [latest, ...prev];
      });
      return;
    }

    // Sort chronologically (oldest to newest) for left-to-right area chart
    const chronological = [...transactions].reverse();
    const formatted = chronological.map((tx) => {
      const score = Number(tx.risk_score || 0);
      let timeStr = '00:00:00';
      if (tx.timestamp) {
        try {
          const d = new Date(tx.timestamp);
          timeStr = d.toTimeString().split(' ')[0] || String(tx.timestamp).slice(11, 19);
        } catch {
          timeStr = String(tx.timestamp).slice(11, 19) || '00:00:00';
        }
      }
      return {
        tx_id: tx.tx_id || '',
        timestamp: timeStr,
        score,
        amount: tx.amount,
        sender: tx.sender_account,
        receiver: tx.receiver_account,
        channel: tx.channel || 'UPI',
        rawTx: tx
      };
    });

    setLiveData(formatted.slice(-windowSize));
  }, [transactions, isLive, windowSize]);

  const handleTogglePause = () => {
    if (isLive) {
      setIsLive(false);
    } else {
      setIsLive(true);
      setBufferQueue([]);
    }
  };

  // Metrics dynamically computed from current displayed rolling window
  const metrics = useMemo(() => {
    if (liveData.length === 0) {
      return { currentRisk: 0, avgRisk: 0, highRiskCount: 0, critRiskCount: 0 };
    }
    const latest = liveData[liveData.length - 1];
    const total = liveData.reduce((acc, curr) => acc + curr.score, 0);
    const avgRisk = Math.round(total / liveData.length);
    const highRiskCount = liveData.filter((t) => t.score >= 70 && t.score < 85).length;
    const critRiskCount = liveData.filter((t) => t.score >= 85).length;

    return {
      currentRisk: latest.score,
      avgRisk,
      highRiskCount,
      critRiskCount
    };
  }, [liveData]);

  // Recent 6 risk event chips (newest first)
  const recentEvents = useMemo(() => {
    return [...liveData].reverse().slice(0, 6);
  }, [liveData]);

  const getRiskColorClass = (score) => {
    if (score >= 85) return 'text-rose-400';
    if (score >= 70) return 'text-amber-400';
    if (score >= 40) return 'text-sky-400';
    return 'text-emerald-400';
  };

  const getChipStyle = (score) => {
    if (score >= 85) {
      return 'bg-[#330F15] border-[#991B1B] text-rose-300 hover:border-rose-400';
    }
    if (score >= 70) {
      return 'bg-[#2E1805] border-[#B45309] text-amber-300 hover:border-amber-400';
    }
    if (score >= 40) {
      return 'bg-[#0B1E3B] border-[#1D4ED8] text-sky-300 hover:border-sky-400';
    }
    return 'bg-[#081220] border-[#1E2D4A] text-slate-300 hover:border-slate-500';
  };

  return (
    <div className="bg-[#070D1A] border border-[#1A2640] rounded-2xl p-6 shadow-2xl flex flex-col justify-between space-y-4 select-none font-sans">
      {/* ── HEADER ROW ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#141E33]">
        <div>
          <div className="flex items-center gap-2.5">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-sky-400" />
              <span>Risk Score Trend</span>
            </h3>

            {/* LIVE Status Badge */}
            {connectionStatus === 'LIVE' && isLive ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-500/50 text-[10px] font-mono font-bold">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                <span>LIVE · LAST {windowSize} TXS</span>
              </span>
            ) : !isLive ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-950/80 text-amber-400 border border-amber-500/50 text-[10px] font-mono font-bold">
                <Pause className="w-2.5 h-2.5 fill-amber-400" />
                <span>PAUSED ({bufferQueue.length})</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-rose-950/80 text-rose-400 border border-rose-500/50 text-[10px] font-mono font-bold">
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                <span>DISCONNECTED</span>
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 font-sans mt-1">
            Real-time risk velocity streaming incoming live feed transaction scores
          </p>
        </div>

        {/* Toolbar Controls */}
        <div className="flex items-center gap-2.5 font-mono text-xs">
          <button
            type="button"
            onClick={handleTogglePause}
            className={`px-3 py-1 rounded-lg font-bold flex items-center gap-1.5 transition-all text-xs ${
              isLive
                ? 'bg-[#0E1B33] border border-[#1E2D4A] text-slate-300 hover:text-white hover:border-slate-500'
                : 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/40'
            }`}
          >
            {isLive ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-white" />}
            <span>{isLive ? 'PAUSE' : 'RESUME LIVE'}</span>
          </button>

          {/* Segmented Window Selector */}
          <div className="inline-flex p-0.5 bg-[#060B14] border border-[#1A2640] rounded-lg text-[11px]">
            {[10, 20, 30, 50].map((sz) => (
              <button
                key={sz}
                type="button"
                onClick={() => setWindowSize(sz)}
                className={`px-2.5 py-0.5 rounded font-bold transition-all ${
                  windowSize === sz
                    ? 'bg-[#0284C7] text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {sz}TX
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── 4-METRIC SUMMARY RIBBON ─────────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-3 p-3 bg-[#060B14]/80 rounded-xl border border-[#1A2640] font-mono text-xs">
        <div>
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block">CURRENT RISK</span>
          <span className={`text-lg font-extrabold ${getRiskColorClass(metrics.currentRisk)}`}>
            {metrics.currentRisk}
          </span>
        </div>
        <div>
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block">AVG RISK</span>
          <span className="text-lg font-extrabold text-slate-100">{metrics.avgRisk}</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block">HIGH RISK</span>
          <span className="text-lg font-extrabold text-amber-400">{metrics.highRiskCount}</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block">CRITICAL</span>
          <span className="text-lg font-extrabold text-rose-400">{metrics.critRiskCount}</span>
        </div>
      </div>

      {/* ── AREA CHART (DEEP RICH BLUE, NO DOT CLUTTER) ────────────────────── */}
      <div className="h-[230px] w-full mt-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={liveData} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
            <defs>
              {/* Deep Rich Blue Area Gradient (Exact Sentinel Spec) */}
              <linearGradient id="riskScoreAreaGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#1E40AF" stopOpacity={0.88} />
                <stop offset="50%" stopColor="#1A3F75" stopOpacity={0.78} />
                <stop offset="100%" stopColor="#0B1A38" stopOpacity={0.65} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1A2640" strokeOpacity={0.6} vertical={false} />
            <XAxis
              dataKey="timestamp"
              stroke="#64748B"
              fontSize={10}
              fontFamily="JetBrains Mono"
              tickLine={false}
              axisLine={{ stroke: '#1A2640' }}
            />
            <YAxis
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              stroke="#64748B"
              fontSize={10}
              fontFamily="JetBrains Mono"
              tickLine={{ stroke: '#1A2640' }}
              axisLine={{ stroke: '#1A2640' }}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload || !payload.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-[#0A1020] border border-[#1E2E4A] rounded-xl p-3 shadow-2xl font-mono text-xs text-slate-200 space-y-1">
                    <div className="flex items-center justify-between gap-3 border-b border-[#1E2E4A] pb-1">
                      <span className="text-[10px] text-sky-400 font-bold">{d.tx_id}</span>
                      <span className="text-[10px] text-slate-400">{d.timestamp}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3 pt-1">
                      <span className="text-slate-400 text-[10px]">RISK SCORE</span>
                      <span className={`font-extrabold ${getRiskColorClass(d.score)}`}>{d.score}</span>
                    </div>
                    {d.amount && (
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-slate-400 text-[10px]">AMOUNT</span>
                        <span className="font-bold text-slate-200">₹{Number(d.amount).toLocaleString('en-IN')}</span>
                      </div>
                    )}
                    {d.channel && (
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-slate-400 text-[10px]">CHANNEL</span>
                        <span className="font-semibold text-slate-300">{d.channel}</span>
                      </div>
                    )}
                  </div>
                );
              }}
            />
            {/* Area without dot clutter */}
            <Area
              type="monotone"
              dataKey="score"
              stroke="#38BDF8"
              strokeWidth={2.2}
              fill="url(#riskScoreAreaGradient)"
              isAnimationActive={false}
              activeDot={{ r: 5, fill: '#38BDF8', stroke: '#070D1A', strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* ── RECENT STREAM RISK EVENTS CHIPS ─────────────────────────────────── */}
      <div className="pt-3 border-t border-[#141E33] space-y-2">
        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block">
          Recent Stream Risk Events
        </span>
        <div className="flex flex-wrap gap-2 text-xs font-mono">
          {recentEvents.map((evt) => (
            <button
              key={evt.tx_id}
              type="button"
              onClick={() => {
                setSelectedPoint(evt);
                if (onSelectTransaction) onSelectTransaction(evt.rawTx || evt);
              }}
              className={`px-2.5 py-1 rounded-lg border flex items-center gap-2 transition-all shadow-sm ${getChipStyle(
                evt.score
              )}`}
              title={`Inspect ${evt.tx_id} (Risk Score: ${evt.score})`}
            >
              <span className="font-extrabold">{evt.score}</span>
              <span className="text-slate-400 text-[10.5px] tracking-tight">{evt.tx_id}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Optional Selected Point Quick Inspector Modal / Popover */}
      {selectedPoint && (
        <div className="p-3 bg-[#0B1528] border border-sky-500/30 rounded-xl flex items-center justify-between text-xs font-mono animate-fadeIn">
          <div className="flex items-center gap-3">
            <span className="text-sky-400 font-bold">{selectedPoint.tx_id}</span>
            <span className="text-slate-400 text-[11px]">{selectedPoint.timestamp}</span>
            <span className={`font-bold ${getRiskColorClass(selectedPoint.score)}`}>
              Score: {selectedPoint.score}
            </span>
            {selectedPoint.amount && (
              <span className="text-slate-300">₹{Number(selectedPoint.amount).toLocaleString('en-IN')}</span>
            )}
          </div>
          <button
            onClick={() => setSelectedPoint(null)}
            className="text-slate-400 hover:text-slate-200 text-xs font-bold px-2 py-0.5 rounded hover:bg-[#14223D]"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
};

export default RiskScoreTrend;
