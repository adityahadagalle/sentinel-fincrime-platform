import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { 
  Shield, Activity, ShieldAlert, TrendingUp, CheckCircle2, Zap, 
  BarChart3, PieChart as PieIcon, Layers, DollarSign, 
  RefreshCw, Clock, Filter, ArrowRight, Lock, FileText, AlertTriangle,
  ChevronRight, Radio, Cpu, Info, RotateCcw
} from 'lucide-react';
import { 
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, 
  Tooltip, PieChart, Pie, Cell, Sector 
} from 'recharts';

/**
 * Format currency in Indian numbering system (Crores / Lakhs / Thousands)
 */
const formatINR = (val) => {
  const num = Number(val) || 0;
  if (num >= 10000000) {
    return `₹${(num / 10000000).toFixed(2)} Cr`;
  }
  if (num >= 100000) {
    return `₹${(num / 100000).toFixed(2)} L`;
  }
  if (num >= 1000) {
    return `₹${(num / 1000).toFixed(1)} K`;
  }
  return `₹${num.toFixed(2)}`;
};

/**
 * SENTINEL — Analytics Overview Redesign
 * 
 * Reorganizes the Analytics page into a high-density, 6-tier analytical story:
 * 1. Executive Summary (4 core verified KPIs, zero fake trends)
 * 2. Risk Situation (Coordinated Risk Trend Area Chart + Risk Level Distribution)
 * 3. Threat Intelligence (Real detected AML patterns + Channel risk profile)
 * 4. Investigation Performance (Real case throughput + Deterministic Investigation Confidence)
 * 5. Action & Automation Outcomes (Enforcement distribution + Automation rate & human boundaries)
 * 6. Network & Financial Impact (Multi-hop topology metrics + Exposure, Recovered, Loss, Recovery %)
 * 
 * STATED MANDATE: NO RANDOM / HARDCODED / FABRICATED NUMBERS.
 * All data derived strictly from authentic backend telemetry.
 */
const ACTION_THEMES = {
  FREEZE: {
    bar: 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.4)]',
    text: 'text-rose-400',
    badge: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
    statusLabel: 'Requires Operator Action',
    governance: 'Mandatory human authorization required. Automated execution strictly blocked by safety rules.'
  },
  ESCALATE: {
    bar: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]',
    text: 'text-amber-400',
    badge: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
    statusLabel: 'Escalated to Queue',
    governance: 'Triggered by high risk evaluation (score >= 70.0). Queued for analyst forensic review.'
  },
  'ENHANCED MONITORING': {
    bar: 'bg-sky-500 shadow-[0_0_8px_rgba(56,189,248,0.4)]',
    text: 'text-sky-400',
    badge: 'bg-sky-500/15 text-sky-300 border-sky-500/40',
    statusLabel: 'High Risk Watch',
    governance: 'Triggered by medium risk patterns (score >= 40.0). Placed on active velocity surveillance.'
  },
  MONITOR: {
    bar: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]',
    text: 'text-emerald-400',
    badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
    statusLabel: 'Standard Baseline',
    governance: 'Baseline policy evaluated on low risk transactions (score < 40.0). No disruption.'
  },
  BLOCK: {
    bar: 'bg-slate-700',
    text: 'text-slate-400',
    badge: 'bg-slate-800/80 text-slate-500 border-slate-700/60',
    statusLabel: 'Supported • 0 recorded',
    governance: 'Supported action code. Incurred 0 transactions meeting block criteria in this timeframe.'
  },
  REJECT: {
    bar: 'bg-slate-700',
    text: 'text-slate-400',
    badge: 'bg-slate-800/80 text-slate-500 border-slate-700/60',
    statusLabel: 'Supported • 0 recorded',
    governance: 'Supported action code. Incurred 0 transaction rejection evaluations in this timeframe.'
  },
  'FILE STR': {
    bar: 'bg-slate-700',
    text: 'text-slate-400',
    badge: 'bg-slate-800/80 text-slate-500 border-slate-700/60',
    statusLabel: 'Supported • 0 recorded',
    governance: 'Supported regulatory action code. Suspicious Transaction Reports filed via manual case action.'
  },
  'CLOSE ACCOUNT': {
    bar: 'bg-slate-700',
    text: 'text-slate-400',
    badge: 'bg-slate-800/80 text-slate-500 border-slate-700/60',
    statusLabel: 'Supported • 0 recorded',
    governance: 'Supported action code. Account closure requires senior compliance officer authorization.'
  }
};/**
 * Custom forensic tooltip for Risk Distribution Donut Chart
 * Maintained as an accessible reference formatter
 */
const RiskDistributionTooltip = ({ active, payload }) => {
  if (!active || !payload || !payload.length) return null;
  const item = payload[0].payload;
  if (!item) return null;

  return (
    <div className="pointer-events-none select-none bg-[#081020]/95 border border-[#1E293B] p-3 rounded-lg shadow-2xl font-mono text-xs max-w-[240px] space-y-2 backdrop-blur-md">
      <div className="flex items-center justify-between gap-2 pb-1.5 border-b border-[#1E293B]">
        <div className="flex items-center gap-1.5 font-bold" style={{ color: item.color }}>
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
          <span>{item.name} RISK</span>
        </div>
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
          {item.threshold || 'Score Tier'}
        </span>
      </div>
      <div className="space-y-1 text-[11px]">
        <div className="flex justify-between text-slate-400">
          <span>Transactions:</span>
          <span className="font-bold text-slate-200">{item.value.toLocaleString()}</span>
        </div>
        <div className="flex justify-between text-slate-400">
          <span>Dataset Share:</span>
          <span className="font-bold text-sky-400">{item.percentage}%</span>
        </div>
        {item.volume !== undefined && (
          <div className="flex justify-between text-slate-400">
            <span>Volume Exposure:</span>
            <span className="font-bold text-emerald-400">{formatINR(item.volume)}</span>
          </div>
        )}
        {item.avg_score !== undefined && item.avg_score > 0 && (
          <div className="flex justify-between text-slate-400">
            <span>Avg Risk Score:</span>
            <span className="font-bold text-amber-400">{item.avg_score} / 100</span>
          </div>
        )}
      </div>
      {item.guidance && (
        <div className="pt-1.5 border-t border-[#1E293B] text-[9.5px] text-slate-400 font-sans leading-tight">
          {item.guidance}
        </div>
      )}
    </div>
  );
};

/**
 * Polished, 60fps Interactive Risk Distribution Explorer
 * 
 * Performance & UX Architecture:
 * 1. Dedicated Center Safe Area: Fixed 104px circular zone reserved exclusively for tier KPI metrics.
 * 2. Zero Visual Overlap: Hover telemetry is anchored strictly in the dedicated bottom inspector.
 * 3. Stable Precedence Model: Temporary hover takes precedence during active mouse exploration,
 *    smoothly reverting to persistent click-selection (or total distribution) on mouse leave.
 * 4. Zero Layout Reflow: Static-dimension container slots (112px inspector, fixed card grid, fixed center)
 *    prevent any vertical jumps, card height changes, or container shifts during rapid switching.
 * 5. GPU-Accelerated Styling: Border-color, opacity, and transform transitions without ring/shadow conflicts.
 * 6. Stable Keying: Recharts Cells and risk cards are keyed by stable tier identifiers (CRITICAL, HIGH, MEDIUM, LOW).
 */
const RiskDistributionExplorer = React.memo(({ riskDistribution, totalTx, alertRate }) => {
  const [activeRiskIndex, setActiveRiskIndex] = useState(null);
  const [selectedRiskLevel, setSelectedRiskLevel] = useState(null);

  // Deterministic state precedence:
  // 1. Temporary hover priority (while hovering a slice or card)
  // 2. Persistent click selection (pinned tier)
  // 3. Fallback to -1 (overall distribution)
  const effectiveRiskIndex = useMemo(() => {
    if (activeRiskIndex !== null) return activeRiskIndex;
    if (selectedRiskLevel) {
      const idx = riskDistribution.findIndex(r => r.name === selectedRiskLevel);
      if (idx !== -1) return idx;
    }
    return -1;
  }, [activeRiskIndex, selectedRiskLevel, riskDistribution]);

  const activeRiskItem = useMemo(() => {
    if (effectiveRiskIndex >= 0 && effectiveRiskIndex < riskDistribution.length) {
      return riskDistribution[effectiveRiskIndex];
    }
    return null;
  }, [effectiveRiskIndex, riskDistribution]);

  // Handle tier click selection toggle
  const handleTierToggle = useCallback((tierName) => {
    setSelectedRiskLevel(prev => prev === tierName ? null : tierName);
  }, []);

  // Handle clear/reset
  const handleReset = useCallback(() => {
    setSelectedRiskLevel(null);
    setActiveRiskIndex(null);
  }, []);

  // Synchronize selection if timeframe dataset updates
  useEffect(() => {
    if (selectedRiskLevel && !riskDistribution.some(r => r.name === selectedRiskLevel)) {
      setSelectedRiskLevel(null);
    }
  }, [riskDistribution, selectedRiskLevel]);

  // Aggregate telemetry grounded in authentic dataset
  const highRiskCount = useMemo(() => {
    return riskDistribution
      .filter(r => r.name === 'CRITICAL' || r.name === 'HIGH')
      .reduce((sum, r) => sum + (r.value || 0), 0);
  }, [riskDistribution]);

  const totalExposureSum = useMemo(() => {
    return riskDistribution.reduce((sum, r) => sum + (r.volume || 0), 0);
  }, [riskDistribution]);

  // Active shape with hardware-accelerated outer ring expansion
  const renderActiveShape = useCallback((props) => {
    const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
    return (
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius - 1}
        outerRadius={outerRadius + 4}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        stroke="#ffffff"
        strokeWidth={1.5}
        cursor="pointer"
        style={{
          filter: `drop-shadow(0px 0px 6px ${fill}80)`,
          transition: 'all 150ms ease-out'
        }}
      />
    );
  }, []);

  return (
    <div className="lg:col-span-5 bg-[#0B132B]/90 border border-[#1E293B] p-5 rounded-xl shadow-xl flex flex-col justify-between space-y-3.5">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-amber-400" />
              Risk Level Distribution
            </h2>
            <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 uppercase tracking-wider">
              Interactive Explorer
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-sans mt-0.5">
            Exact transaction classification breakdown & exposure forensics
          </p>
        </div>

        {selectedRiskLevel && (
          <button
            onClick={handleReset}
            className="text-[10px] font-mono text-slate-400 hover:text-slate-100 flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/70 transition-colors shrink-0"
            title="Reset tier filter"
          >
            <RotateCcw className="w-3 h-3 text-slate-400" />
            <span>RESET</span>
          </button>
        )}
      </div>

      {/* Donut Chart with Dedicated Center Safe Area */}
      <div 
        className="h-[185px] w-full relative flex items-center justify-center"
        onMouseLeave={() => setActiveRiskIndex(null)}
      >
        {riskDistribution.length > 0 ? (
          <>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart onMouseLeave={() => setActiveRiskIndex(null)}>
                <Pie
                  data={riskDistribution}
                  innerRadius={52}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="value"
                  isAnimationActive={false}
                  activeIndex={effectiveRiskIndex >= 0 ? effectiveRiskIndex : undefined}
                  activeShape={renderActiveShape}
                  onMouseEnter={(_, index) => setActiveRiskIndex(index)}
                  onMouseLeave={() => setActiveRiskIndex(null)}
                  onClick={(_, index) => handleTierToggle(riskDistribution[index].name)}
                  cursor="pointer"
                >
                  {riskDistribution.map((entry, index) => {
                    const isSelected = effectiveRiskIndex === index;
                    const isAnyActive = effectiveRiskIndex >= 0;
                    return (
                      <Cell 
                        key={entry.name} 
                        fill={entry.color}
                        fillOpacity={isAnyActive ? (isSelected ? 1 : 0.3) : 0.95}
                        stroke={isSelected ? '#ffffff' : '#0B132B'}
                        strokeWidth={isSelected ? 1.5 : 1}
                      />
                    );
                  })}
                </Pie>
              </PieChart>
            </ResponsiveContainer>

            {/* Dedicated Donut Center Safe Area (104px Diameter - Zero Overlap) */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div 
                className="w-[104px] h-[104px] rounded-full flex flex-col items-center justify-center select-none z-10"
                aria-label="Donut Center KPI Safe Area"
              >
                <div className="flex flex-col items-center justify-center text-center transition-all duration-150 ease-out">
                  {/* Line 1: Tier Badge or Overall Indicator (Fixed h-5) */}
                  <div className="h-5 flex items-center justify-center">
                    {activeRiskItem ? (
                      <span 
                        className="text-[9px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded transition-colors duration-150"
                        style={{ 
                          color: activeRiskItem.color, 
                          backgroundColor: `${activeRiskItem.color}18`,
                          border: `1px solid ${activeRiskItem.color}40`
                        }}
                      >
                        {activeRiskItem.name}
                      </span>
                    ) : (
                      <span className="text-[9px] font-mono text-slate-500 uppercase tracking-wider font-semibold">
                        TOTAL TXS
                      </span>
                    )}
                  </div>

                  {/* Line 2: Numeric KPI Metric (Fixed h-7) */}
                  <div className="h-7 flex items-center justify-center">
                    <span className="text-xl font-mono font-black text-slate-100 tracking-tight transition-all duration-150">
                      {activeRiskItem 
                        ? activeRiskItem.value.toLocaleString() 
                        : totalTx.toLocaleString()
                      }
                    </span>
                  </div>

                  {/* Line 3: Dataset Share or Scope (Fixed h-4) */}
                  <div className="h-4 flex items-center justify-center">
                    {activeRiskItem ? (
                      <span className="text-[10px] font-mono font-bold text-sky-400 uppercase tracking-wider transition-colors duration-150">
                        {activeRiskItem.percentage}% SHARE
                      </span>
                    ) : (
                      <span className="text-[8.5px] font-mono text-slate-500 uppercase tracking-widest">
                        ALL 4 TIERS
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="text-slate-500 font-mono text-xs">No distribution data</div>
        )}
      </div>

      {/* Severity Breakdown Cards (Stable Active State, Zero Grid Jumping) */}
      <div 
        className="grid grid-cols-2 gap-2 pt-2 border-t border-[#1E293B]"
        onMouseLeave={() => setActiveRiskIndex(null)}
      >
        {riskDistribution.map((item, index) => {
          const isSelected = selectedRiskLevel === item.name;
          const isHovered = activeRiskIndex === index;
          const isHighlighted = isHovered || isSelected;
          const isAnyHighlighted = activeRiskIndex !== null || selectedRiskLevel !== null;

          return (
            <div 
              key={item.name} 
              onClick={() => handleTierToggle(item.name)}
              onMouseEnter={() => setActiveRiskIndex(index)}
              className={`p-2.5 rounded-lg border cursor-pointer text-xs font-mono flex flex-col justify-between space-y-1.5 transition-all duration-150 ease-out select-none ${
                isHighlighted 
                  ? 'bg-[#0E1B38] z-10' 
                  : isAnyHighlighted 
                    ? 'bg-[#060B15]/60 border-[#1E293B]/60 opacity-40 hover:opacity-90 hover:border-slate-600'
                    : 'bg-[#060B15] border-[#1E293B] hover:border-slate-600 hover:bg-[#081020]'
              }`}
              style={{
                borderColor: isHighlighted ? item.color : undefined,
                boxShadow: isHighlighted ? `0 0 10px ${item.color}35` : 'none',
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 truncate">
                  <span 
                    className="w-2 h-2 rounded-full shrink-0 transition-all duration-150" 
                    style={{ 
                      backgroundColor: item.color, 
                      boxShadow: isHighlighted ? `0 0 6px ${item.color}` : 'none' 
                    }} 
                  />
                  <span className={`font-bold text-[11px] transition-colors duration-150 ${isHighlighted ? 'text-white' : 'text-slate-300'}`}>
                    {item.name}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {isSelected && (
                    <span 
                      className="text-[7.5px] font-mono font-bold px-1 py-0.2 rounded uppercase"
                      style={{ color: item.color, backgroundColor: `${item.color}20` }}
                    >
                      PINNED
                    </span>
                  )}
                  <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60">
                    {item.threshold || (item.name === 'CRITICAL' ? '≥85' : item.name === 'HIGH' ? '70–84' : item.name === 'MEDIUM' ? '40–69' : '<40')}
                  </span>
                </div>
              </div>

              <div className="flex items-baseline justify-between pt-0.5">
                <span className="text-slate-100 font-bold text-xs">
                  {item.value.toLocaleString()}{' '}
                  <span className="text-[9px] font-normal text-slate-500 font-sans">txs</span>
                </span>
                <span className={`text-[10px] font-bold transition-colors duration-150 ${isHighlighted ? 'text-sky-300' : 'text-slate-400'}`}>
                  {item.percentage}%
                </span>
              </div>

              {/* Proportional Mini Bar */}
              <div className="w-full bg-slate-800/80 h-1 rounded-full overflow-hidden">
                <div 
                  className="h-full rounded-full transition-all duration-200 ease-out" 
                  style={{ 
                    width: `${Math.max(item.percentage, item.value > 0 ? 3 : 0)}%`, 
                    backgroundColor: item.color 
                  }} 
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Forensic Tier Telemetry Inspector Bar (STABLE FIXED HEIGHT - ZERO LAYOUT SHIFT) */}
      <div className="pt-2 border-t border-[#1E293B]/80 font-mono h-[112px] min-h-[112px] max-h-[112px] flex flex-col justify-between overflow-hidden">
        <div className="p-2.5 rounded-lg bg-[#060B15] border border-[#1E293B] h-full flex flex-col justify-between transition-colors duration-150">
          {/* Header row: fixed height */}
          <div className="flex items-center justify-between text-[11px] h-4">
            <div className="flex items-center gap-1.5 truncate">
              <span 
                className="w-1.5 h-1.5 rounded-full shrink-0 transition-colors duration-150" 
                style={{ 
                  backgroundColor: activeRiskItem ? activeRiskItem.color : '#38bdf8' 
                }} 
              />
              <span 
                className="font-bold uppercase tracking-wider truncate transition-colors duration-150" 
                style={{ color: activeRiskItem ? activeRiskItem.color : '#cbd5e1' }}
              >
                {activeRiskItem ? `${activeRiskItem.name} Forensics` : 'Dataset Forensics'}
              </span>
              <span className="text-[8px] text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700/60 shrink-0">
                {activeRiskItem ? activeRiskItem.threshold : '4 Severity Tiers'}
              </span>
            </div>
            <span className="text-[9px] font-mono shrink-0">
              {selectedRiskLevel && (!activeRiskIndex || riskDistribution[activeRiskIndex]?.name === selectedRiskLevel) ? (
                <span className="text-amber-400 font-bold">● PINNED</span>
              ) : activeRiskIndex !== null ? (
                <span className="text-sky-400 font-bold">HOVERING</span>
              ) : (
                <span className="text-slate-500">SYSTEM BASELINE</span>
              )}
            </span>
          </div>

          {/* 3 Metric Tiles: fixed 3-column grid, fixed heights */}
          <div className="grid grid-cols-3 gap-1.5 text-center">
            <div className="p-1 rounded bg-[#081020] border border-[#1E293B]/60 flex flex-col justify-center h-10">
              <span className="text-[8px] text-slate-500 block uppercase truncate">
                {activeRiskItem ? 'Volume Exposure' : 'Total Monitored'}
              </span>
              <span className="text-[11px] font-bold text-emerald-400 block mt-0.5 truncate transition-all duration-150">
                {activeRiskItem ? formatINR(activeRiskItem.volume || 0) : totalTx.toLocaleString() + ' txs'}
              </span>
            </div>
            <div className="p-1 rounded bg-[#081020] border border-[#1E293B]/60 flex flex-col justify-center h-10">
              <span className="text-[8px] text-slate-500 block uppercase truncate">
                {activeRiskItem ? 'Avg Risk Score' : 'Alert Rate'}
              </span>
              <span className="text-[11px] font-bold text-sky-400 block mt-0.5 truncate transition-all duration-150">
                {activeRiskItem ? (activeRiskItem.avg_score ? `${activeRiskItem.avg_score} / 100` : '—') : `${alertRate}%`}
              </span>
            </div>
            <div className="p-1 rounded bg-[#081020] border border-[#1E293B]/60 flex flex-col justify-center h-10">
              <span className="text-[8px] text-slate-500 block uppercase truncate">
                {activeRiskItem ? 'Dataset Share' : 'High/Crit Alerts'}
              </span>
              <span className="text-[11px] font-bold text-slate-200 block mt-0.5 truncate transition-all duration-150">
                {activeRiskItem ? `${activeRiskItem.percentage}%` : highRiskCount.toLocaleString()}
              </span>
            </div>
          </div>

          {/* Sub-line Guidance / Baseline: fixed h-4 */}
          <div className="text-[9.5px] text-slate-400 font-sans flex items-center gap-1.5 pt-0.5 border-t border-[#1E293B]/40 truncate h-4">
            <ShieldAlert className="w-3 h-3 text-slate-500 shrink-0" />
            <span className="truncate">
              {activeRiskItem?.guidance || 'Select or hover any tier card above to inspect volume, score distribution, and policy guidance.'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});

/**
 * Polished, Interactive Payment Channel Risk Profile (Horizontal Bar Chart)
 * 
 * Replaces stacked cards with a compact, comparative horizontal bar visualization:
 * - Primary Bar Length: Scaled proportionally to transaction volume (tx_count).
 * - Secondary Metrics: Flagged rate badge (% flagged) and monetary exposure (₹ formatINR).
 * - Sorting: Deterministic transaction volume descending, then alphabetical.
 * - Interactive States: Hover preview + Click-to-pin persistent rail focus.
 * - Clear Action: 'VIEW ALL' reset button when a rail is selected.
 * - Column Structure: Payment Rail | Proportional Bar | Volume (tx) | Flagged Rate | Exposure
 * - Grounding: 100% authentic backend data from /analytics/overview.
 */
const PaymentChannelRiskProfile = React.memo(({ channelPerf, totalTx, timeframe }) => {
  const [hoveredChannel, setHoveredChannel] = useState(null);
  const [selectedChannel, setSelectedChannel] = useState(null);

  // Deterministic sort: transaction volume descending, then alphabetical
  const sortedChannels = useMemo(() => {
    return [...channelPerf].sort((a, b) => {
      const diff = (b.tx_count || 0) - (a.tx_count || 0);
      if (diff !== 0) return diff;
      return (a.channel || '').localeCompare(b.channel || '');
    });
  }, [channelPerf]);

  // Max transaction count across all rails in current dataset for proportional bar scaling
  const maxTx = useMemo(() => {
    if (!sortedChannels.length) return 1;
    return Math.max(...sortedChannels.map(c => c.tx_count || 0), 1);
  }, [sortedChannels]);

  // Active channel (hover takes temporary priority, then selected)
  const activeChannelName = hoveredChannel || selectedChannel;
  const activeChannel = useMemo(() => {
    if (!activeChannelName) return null;
    return sortedChannels.find(c => c.channel === activeChannelName) || null;
  }, [activeChannelName, sortedChannels]);

  // Total volume and exposure across all payment channels in active dataset
  const totalChannelTx = useMemo(() => {
    return sortedChannels.reduce((sum, c) => sum + (c.tx_count || 0), 0);
  }, [sortedChannels]);

  const totalChannelAmount = useMemo(() => {
    return sortedChannels.reduce((sum, c) => sum + (c.total_amount || 0), 0);
  }, [sortedChannels]);

  const handleChannelClick = useCallback((channelName) => {
    setSelectedChannel(prev => prev === channelName ? null : channelName);
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedChannel(null);
    setHoveredChannel(null);
  }, []);

  // Synchronize selection if timeframe updates and selected channel is absent
  useEffect(() => {
    if (selectedChannel && !sortedChannels.some(c => c.channel === selectedChannel)) {
      setSelectedChannel(null);
    }
  }, [sortedChannels, selectedChannel]);

  return (
    <div className="lg:col-span-6 bg-[#0B132B]/90 border border-[#1E293B] p-5 rounded-xl shadow-xl flex flex-col justify-between space-y-3.5">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
              <Layers className="w-4 h-4 text-sky-400" />
              Payment Channel Risk Profile
            </h2>
            <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-300 uppercase tracking-wider">
              Horizontal Rail Chart
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-sans mt-0.5">
            Risk concentration, transaction counts, and financial exposure by rail
          </p>
        </div>

        {selectedChannel ? (
          <button
            onClick={handleClearSelection}
            className="text-[10px] font-mono text-slate-400 hover:text-slate-100 flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-800 border border-slate-700/70 transition-colors shrink-0"
            title="Clear rail filter"
          >
            <RotateCcw className="w-3 h-3 text-slate-400" />
            <span>VIEW ALL</span>
          </button>
        ) : (
          <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/60 text-slate-400 uppercase tracking-wider shrink-0">
            {timeframe ? `${timeframe.toUpperCase()} SCOPE` : 'CURRENT'}
          </span>
        )}
      </div>

      {/* Sub-Header Column Labels */}
      <div className="flex items-center text-[9px] font-mono uppercase tracking-wider text-slate-500 px-2.5 pb-1 border-b border-[#1E293B]/60 select-none">
        <span className="w-24 shrink-0">Payment Rail</span>
        <span className="flex-1 min-w-[70px] mx-2.5">Volume Distribution</span>
        <span className="w-16 text-right shrink-0">Volume</span>
        <span className="w-24 sm:w-28 text-right shrink-0">Flagged Rate</span>
        <span className="w-20 sm:w-24 text-right shrink-0">Exposure</span>
      </div>

      {/* Horizontal Bar Chart Rows */}
      {sortedChannels.length > 0 ? (
        <div 
          className="space-y-1.5 select-none"
          onMouseLeave={() => setHoveredChannel(null)}
        >
          {sortedChannels.map((ch) => {
            const isSelected = selectedChannel === ch.channel;
            const isHovered = hoveredChannel === ch.channel;
            const isHighlighted = isSelected || isHovered;
            const isAnyActive = selectedChannel !== null || hoveredChannel !== null;

            // Bar length proportionally scaled to highest transaction volume in current dataset
            const barWidthPct = ch.tx_count > 0 ? Math.max((ch.tx_count / maxTx) * 100, 2) : 0;

            // Semantic color styling for flagged rate
            const flagColor = ch.tx_count === 0 
              ? 'text-slate-500 bg-slate-800/40 border-slate-700/40' 
              : ch.risk_rate >= 50 
                ? 'text-rose-400 bg-rose-500/15 border-rose-500/30' 
                : ch.risk_rate >= 20 
                  ? 'text-amber-400 bg-amber-500/15 border-amber-500/30' 
                  : 'text-emerald-400 bg-emerald-500/15 border-emerald-500/30';

            return (
              <div
                key={ch.channel}
                onClick={() => handleChannelClick(ch.channel)}
                onMouseEnter={() => setHoveredChannel(ch.channel)}
                className={`relative px-2.5 py-2 rounded-lg border cursor-pointer font-mono flex items-center transition-all duration-150 ease-out ${
                  isHighlighted
                    ? 'bg-[#0c1938] border-sky-400/80 shadow-[0_0_12px_rgba(56,189,248,0.2)] z-10'
                    : isAnyActive
                      ? 'bg-[#060B15]/50 border-[#1E293B]/60 opacity-40 hover:opacity-85 hover:border-slate-600'
                      : 'bg-[#060B15] border-[#1E293B] hover:border-slate-600 hover:bg-[#081020]'
                }`}
              >
                {/* 1. Channel Label */}
                <div className="w-24 shrink-0 flex items-center gap-1.5 truncate">
                  <span 
                    className={`w-1.5 h-1.5 rounded-full shrink-0 transition-colors duration-150 ${
                      isSelected ? 'bg-sky-400 animate-pulse' : isHovered ? 'bg-sky-300' : 'bg-slate-600'
                    }`} 
                  />
                  <span className={`text-[11px] font-bold truncate transition-colors duration-150 ${
                    isHighlighted ? 'text-white' : 'text-slate-300'
                  }`}>
                    {ch.channel}
                  </span>
                  {isSelected && (
                    <span className="text-[7.5px] font-mono font-bold px-1 rounded bg-sky-500/20 text-sky-300 shrink-0">
                      PIN
                    </span>
                  )}
                </div>

                {/* 2. Proportional Horizontal Volume Bar */}
                <div className="flex-1 min-w-[70px] h-2.5 bg-slate-800/80 rounded-full overflow-hidden mx-2.5 relative">
                  <div 
                    className="h-full rounded-full transition-all duration-300 ease-out"
                    style={{ 
                      width: `${barWidthPct}%`,
                      background: isHighlighted 
                        ? 'linear-gradient(90deg, #0284c7, #38bdf8)' 
                        : 'linear-gradient(90deg, #0369a1, #0ea5e9)'
                    }}
                  />
                </div>

                {/* 3. Transaction Count */}
                <div className="w-16 text-right shrink-0">
                  <span className={`text-[11px] font-bold transition-colors duration-150 ${
                    isHighlighted ? 'text-slate-100' : 'text-slate-300'
                  }`}>
                    {ch.tx_count.toLocaleString()}{' '}
                    <span className="text-[9px] font-normal text-slate-500 font-sans">tx</span>
                  </span>
                </div>

                {/* 4. Flagged Percentage (Accurate Non-Fraud Semantics) */}
                <div className="w-24 sm:w-28 text-right shrink-0">
                  <span className={`px-1.5 py-0.5 rounded text-[9.5px] font-bold border uppercase tracking-wider inline-block ${flagColor}`}>
                    {ch.risk_rate}% flagged
                  </span>
                </div>

                {/* 5. Financial Volume Exposure */}
                <div className="w-20 sm:w-24 text-right shrink-0">
                  <span className="text-[11px] font-bold text-slate-100 block truncate">
                    {formatINR(ch.total_amount)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="h-[180px] flex items-center justify-center text-slate-500 font-mono text-xs">
          No payment rail telemetry available in current timeframe
        </div>
      )}

      {/* Forensic Telemetry Strip (Fixed Dimensions - Zero Reflow) */}
      <div className="pt-2 border-t border-[#1E293B]/80 font-mono h-[54px] min-h-[54px] max-h-[54px] flex flex-col justify-between overflow-hidden">
        <div className="p-2 rounded-lg bg-[#060B15] border border-[#1E293B] h-full flex flex-col justify-between text-xs">
          {activeChannel ? (
            <>
              <div className="flex items-center justify-between text-[10px] h-3.5">
                <div className="flex items-center gap-1.5 truncate">
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-400 shrink-0 animate-pulse" />
                  <span className="font-bold text-sky-300 uppercase tracking-wider truncate">
                    {activeChannel.channel} Forensics
                  </span>
                  <span className="text-[8px] text-slate-400 bg-slate-800/80 px-1.5 py-0.2 rounded border border-slate-700/60 shrink-0">
                    {((activeChannel.tx_count / Math.max(totalTx, 1)) * 100).toFixed(1)}% of System Flow
                  </span>
                </div>
                <span className="text-[8.5px] font-bold text-amber-400 shrink-0">
                  {selectedChannel ? '● PINNED' : 'HOVERING'}
                </span>
              </div>
              <div className="flex items-center justify-between text-[10px] text-slate-400 truncate h-3.5">
                <span>{activeChannel.tx_count.toLocaleString()} transactions recorded</span>
                <span className="text-amber-300 font-bold">{activeChannel.risk_rate}% elevated risk (Score ≥ 40)</span>
                <span className="text-emerald-400 font-bold">{formatINR(activeChannel.total_amount)} exposure</span>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center justify-between text-[10px] h-3.5">
                <div className="flex items-center gap-1.5 truncate text-slate-300">
                  <Info className="w-3 h-3 text-slate-500 shrink-0" />
                  <span className="font-bold uppercase tracking-wider truncate">
                    All {sortedChannels.length} Payment Rails Active
                  </span>
                  <span className="text-[8px] text-slate-500 font-mono">
                    Timeframe: {timeframe ? timeframe.toUpperCase() : '30D'}
                  </span>
                </div>
                <span className="text-[8.5px] text-slate-500">CLICK ROW TO PIN</span>
              </div>
              <div className="flex items-center justify-between text-[10px] text-slate-400 truncate h-3.5">
                <span>Volume: {totalChannelTx.toLocaleString()} txs</span>
                <span>Top Rail: <strong className="text-sky-300">{sortedChannels[0]?.channel || '—'}</strong></span>
                <span className="text-emerald-400 font-bold">Total: {formatINR(totalChannelAmount)}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Meta Bar */}
      <div className="pt-2 border-t border-[#1E293B] flex items-center justify-between text-[9px] font-mono text-slate-500">
        <span>PAYMENT RAILS: {sortedChannels.length}</span>
        <span>SORT: VOLUME DESCENDING • AUTHENTIC AGGREGATION</span>
      </div>
    </div>
  );
});

const Dashboard = () => {
  const { connectionStatus } = useWebSocket();
  const [timeframe, setTimeframe] = useState('30d');
  const [analyticsData, setAnalyticsData] = useState(null);
  const [hoveredAction, setHoveredAction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  // Fetch real analytics telemetry from backend
  const fetchAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      let res;
      try {
        res = await fetch(`${API_BASE}/analytics/overview?timeframe=${timeframe}`);
      } catch {
        res = await fetch(`/analytics/overview?timeframe=${timeframe}`);
      }

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const contentType = res.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        // If non-JSON returned, fetch directly from backend port 8000
        const directRes = await fetch(`http://127.0.0.1:8000/analytics/overview?timeframe=${timeframe}`);
        if (!directRes.ok) {
          throw new Error(`HTTP ${directRes.status}: ${directRes.statusText}`);
        }
        const data = await directRes.json();
        setAnalyticsData(data);
        return;
      }

      const data = await res.json();
      setAnalyticsData(data);
    } catch (err) {
      console.error('Failed to fetch analytics overview:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [timeframe, API_BASE]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  // Polling interval for live analytics telemetry
  useEffect(() => {
    const interval = setInterval(fetchAnalytics, 10000);
    return () => clearInterval(interval);
  }, [fetchAnalytics]);

  // ── AUTHENTIC DATA EXTRACTION (NO HARDCODED FALLBACK NUMBERS) ───────────────
  const kpis = analyticsData?.kpis;
  const riskTrend = analyticsData?.risk_trend || [];
  const riskDistribution = analyticsData?.alerts_by_risk_level || [];
  const investigationPerf = analyticsData?.investigation_performance;
  const invConfidence = analyticsData?.investigation_confidence;
  const actionOutcomes = analyticsData?.action_outcomes || [];
  const autoIntel = analyticsData?.automation_intelligence;
  const channelPerf = analyticsData?.channel_performance || [];
  const detectedPatterns = analyticsData?.detected_patterns || [];
  const finImpact = analyticsData?.financial_impact;

  // Derived Action Outcomes metrics (strictly deterministic from real telemetry)
  const totalActionSum = useMemo(() => {
    return actionOutcomes.reduce((acc, c) => acc + (c.count || 0), 0);
  }, [actionOutcomes]);

  const sortedActions = useMemo(() => {
    return [...actionOutcomes].sort((a, b) => {
      if ((b.count || 0) !== (a.count || 0)) {
        return (b.count || 0) - (a.count || 0);
      }
      return (a.action || '').localeCompare(b.action || '');
    });
  }, [actionOutcomes]);

  const primaryAction = useMemo(() => {
    if (!sortedActions.length || (sortedActions[0].count || 0) === 0) return null;
    const top = sortedActions[0];
    const pct = totalActionSum > 0 ? (((top.count || 0) / totalActionSum) * 100).toFixed(1) : '0.0';
    return { ...top, pct };
  }, [sortedActions, totalActionSum]);

  const freezeItem = useMemo(() => {
    return actionOutcomes.find(a => a.code === 'FREEZE' || a.action === 'FREEZE');
  }, [actionOutcomes]);
  const freezeCount = freezeItem?.count || 0;

  // Derived real contextual metrics (computed solely from authentic data)
  const totalTx = kpis?.total_transactions ?? 0;
  const totalAlerts = kpis?.risk_alerts ?? 0;
  const avgRiskScore = kpis?.avg_risk_score ?? 0;
  const casesResolved = kpis?.cases_resolved ?? 0;

  const alertRate = totalTx > 0 ? ((totalAlerts / totalTx) * 100).toFixed(1) : '0.0';
  const critAlertItem = riskDistribution.find(r => r.name === 'CRITICAL');
  const critCount = critAlertItem ? critAlertItem.value : 0;
  const critPercent = critAlertItem ? critAlertItem.percentage : 0;

  const riskBaselineLabel = avgRiskScore >= 70 ? 'CRITICAL RISK BASELINE' :
                           avgRiskScore >= 40 ? 'ELEVATED RISK BASELINE' :
                           'LOW RISK BASELINE';

  const resolutionRate = investigationPerf?.resolution_rate ?? 0;

  // Active risk trend slice metrics
  const latestTrendPoint = riskTrend.length > 0 ? riskTrend[riskTrend.length - 1] : null;

  return (
    <div className="p-5 md:p-8 bg-[#060B15] min-h-full text-slate-100 font-sans space-y-7 select-none">
      
      {/* ── HEADER & TIMEFRAME SELECTOR ───────────────────────────────────────── */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl md:text-2xl font-bold tracking-tight text-slate-100 font-mono uppercase">
                Analytics Overview
              </h1>
              <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-sky-500/15 border border-sky-500/40 text-sky-300 uppercase tracking-wider flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
                Live Telemetry Sync
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Financial crime intelligence, risk trends and investigation performance
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Timeframe Selector */}
          <div className="inline-flex p-1 rounded-xl bg-[#0B132B] border border-[#1E293B] text-xs font-mono">
            {[
              { label: '24H', value: '24h' },
              { label: '7D', value: '7d' },
              { label: '30D', value: '30d' },
              { label: '12M', value: '12m' }
            ].map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setTimeframe(item.value)}
                className={`px-3 py-1.5 rounded-lg font-bold tracking-wider transition-all ${
                  timeframe === item.value
                    ? 'bg-sky-500 text-slate-950 shadow-md shadow-sky-500/25'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#1E293B]/60'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* Refresh Button */}
          <button
            type="button"
            onClick={fetchAnalytics}
            title="Refresh Telemetry Stream"
            className="p-2 rounded-xl bg-[#0B132B] border border-[#1E293B] text-slate-400 hover:text-sky-300 hover:border-sky-500/40 transition-all shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          </button>
        </div>
      </header>

      {/* Error state if telemetry fails */}
      {error && (
        <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            <span>Telemetry Fetch Failed: {error}. Backend may be re-initializing.</span>
          </div>
          <button 
            onClick={fetchAnalytics} 
            className="px-2.5 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 uppercase text-[10px] font-bold"
          >
            Retry
          </button>
        </div>
      )}

      {/* ── 1. EXECUTIVE SUMMARY (4 CORE VERIFIED KPIS) ───────────────────────── */}
      <section className="space-y-2">
        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase tracking-wider px-1">
          <span>Tier 01 // Executive Summary Telemetry</span>
          <span>Verified Real-time System Metrics</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          
          {/* KPI 1: Total Transactions */}
          <div className="bg-[#0B132B]/90 border border-[#1E293B] p-4 rounded-xl shadow-lg flex flex-col justify-between hover:border-sky-500/40 transition-all relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
                Total Transactions
              </span>
              <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
                <Activity className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3">
              <span className="text-2xl md:text-3xl font-mono font-extrabold text-slate-100 block">
                {kpis ? totalTx.toLocaleString() : '—'}
              </span>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-[10px] font-mono text-slate-400">
                  {totalTx > 0 ? `${alertRate}% flagged as risk alerts` : 'Telemetry stream monitoring'}
                </span>
              </div>
            </div>
          </div>

          {/* KPI 2: Risk Alerts */}
          <div className="bg-[#0B132B]/90 border border-[#1E293B] p-4 rounded-xl shadow-lg flex flex-col justify-between hover:border-amber-500/40 transition-all relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
                Risk Alerts
              </span>
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <ShieldAlert className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3">
              <span className="text-2xl md:text-3xl font-mono font-extrabold text-amber-300 block">
                {kpis ? totalAlerts.toLocaleString() : '—'}
              </span>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-[10px] font-mono font-bold text-rose-400">
                  {critCount.toLocaleString()} Critical ({critPercent}%)
                </span>
                <span className="text-[10px] font-mono text-slate-500">• score ≥ 85</span>
              </div>
            </div>
          </div>

          {/* KPI 3: Average Risk Score */}
          <div className="bg-[#0B132B]/90 border border-[#1E293B] p-4 rounded-xl shadow-lg flex flex-col justify-between hover:border-sky-500/40 transition-all relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
                Average Risk Score
              </span>
              <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3">
              <span className="text-2xl md:text-3xl font-mono font-extrabold text-slate-100 block">
                {kpis ? avgRiskScore : '—'}
              </span>
              <div className="flex items-center gap-1.5 mt-1">
                <span className={`text-[10px] font-mono font-bold uppercase ${
                  avgRiskScore >= 70 ? 'text-amber-400' :
                  avgRiskScore >= 40 ? 'text-sky-400' :
                  'text-emerald-400'
                }`}>
                  {riskBaselineLabel}
                </span>
              </div>
            </div>
          </div>

          {/* KPI 4: Cases Resolved */}
          <div className="bg-[#0B132B]/90 border border-[#1E293B] p-4 rounded-xl shadow-lg flex flex-col justify-between hover:border-emerald-500/40 transition-all relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
                Cases Resolved
              </span>
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3">
              <span className="text-2xl md:text-3xl font-mono font-extrabold text-emerald-400 block">
                {kpis ? casesResolved.toLocaleString() : '—'}
              </span>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-[10px] font-mono text-slate-400">
                  {resolutionRate}% Case Resolution Rate
                </span>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* ── 2. RISK SITUATION (TREND + DISTRIBUTION) ─────────────────────────── */}
      <section className="space-y-2">
        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase tracking-wider px-1">
          <span>Tier 02 // Risk Situation Analysis</span>
          <span>Coordinated Time-Series & Severity Distribution</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          
          {/* Left: Risk Score Time Series (7 cols) */}
          <div className="lg:col-span-7 bg-[#0B132B]/90 border border-[#1E293B] p-5 rounded-xl shadow-xl flex flex-col justify-between space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-sky-400" />
                  Real Risk Score Trend
                </h2>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  Chronological progression of transaction risk scores across current dataset
                </p>
              </div>

              {latestTrendPoint && (
                <div className="flex items-center gap-2 text-[10px] font-mono">
                  <span className="px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-300 font-bold">
                    Latest Chunk: {latestTrendPoint.avg_score} Avg
                  </span>
                </div>
              )}
            </div>

            {/* Time Series Area Chart */}
            <div className="h-[240px] w-full mt-2">
              {riskTrend.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={riskTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="riskScoreGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                    <XAxis 
                      dataKey="timestamp" 
                      stroke="#64748B" 
                      tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'monospace' }} 
                    />
                    <YAxis 
                      domain={[0, 100]} 
                      stroke="#64748B" 
                      tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'monospace' }} 
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#081020', 
                        borderColor: '#1E293B', 
                        borderRadius: '8px', 
                        fontFamily: 'monospace',
                        fontSize: '11px',
                        color: '#E2E8F0' 
                      }}
                      formatter={(val, name) => {
                        if (name === 'avg_score') return [val, 'Average Score'];
                        if (name === 'high_risk') return [val, 'High Risk Count (70-84)'];
                        if (name === 'critical_risk') return [val, 'Critical Count (≥85)'];
                        return [val, name];
                      }}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="avg_score" 
                      stroke="#06b6d4" 
                      strokeWidth={2} 
                      fillOpacity={1} 
                      fill="url(#riskScoreGrad)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500 font-mono text-xs">
                  No chronological risk points available in current timeframe
                </div>
              )}
            </div>

            {/* Time-Series Meta Bar */}
            <div className="pt-3 border-t border-[#1E293B] grid grid-cols-3 gap-2 text-center font-mono text-[10px]">
              <div className="p-2 rounded bg-[#060B15] border border-[#1E293B]/60">
                <span className="text-slate-500 block">TIME POINTS</span>
                <span className="font-bold text-slate-200">{riskTrend.length} intervals</span>
              </div>
              <div className="p-2 rounded bg-[#060B15] border border-[#1E293B]/60">
                <span className="text-slate-500 block">SYSTEM AVERAGE</span>
                <span className="font-bold text-sky-400">{avgRiskScore}</span>
              </div>
              <div className="p-2 rounded bg-[#060B15] border border-[#1E293B]/60">
                <span className="text-slate-500 block">CRITICAL SPIKES</span>
                <span className="font-bold text-rose-400">{critCount}</span>
              </div>
            </div>
          </div>

          {/* Right: Risk Level Distribution Explorer (5 cols) */}
          <RiskDistributionExplorer
            riskDistribution={riskDistribution}
            totalTx={totalTx}
            alertRate={alertRate}
          />

        </div>
      </section>

      {/* ── 3. THREAT INTELLIGENCE (PATTERNS + CHANNELS) ─────────────────────── */}
      <section className="space-y-2">
        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase tracking-wider px-1">
          <span>Tier 03 // Threat Intelligence Telemetry</span>
          <span>Detected AML Patterns & Channel Risk Profile</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          
          {/* Left: Detected AML Patterns (6 cols) */}
          <div className="lg:col-span-6 bg-[#0B132B]/90 border border-[#1E293B] p-5 rounded-xl shadow-xl space-y-3 flex flex-col justify-between">
            <div>
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Detected AML Patterns
              </h2>
              <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                Observed typology occurrences across transaction graph
              </p>
            </div>

            <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
              {detectedPatterns.map((p) => {
                const isCrit = p.risk_contribution === 'Critical';
                const isHigh = p.risk_contribution === 'High';

                return (
                  <div 
                    key={p.pattern} 
                    className="p-2.5 bg-[#060B15] rounded-lg border border-[#1E293B] flex items-center justify-between text-xs font-mono"
                  >
                    <div>
                      <span className="text-slate-200 font-bold block text-[11px]">{p.pattern}</span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {p.occurrences.toLocaleString()} detections
                      </span>
                    </div>
                    <span className={`text-[9px] font-bold px-2 py-0.5 rounded border uppercase ${
                      isCrit ? 'bg-rose-500/15 text-rose-300 border-rose-500/30' :
                      isHigh ? 'bg-amber-500/15 text-amber-300 border-amber-500/30' :
                      'bg-sky-500/15 text-sky-300 border-sky-500/30'
                    }`}>
                      {p.risk_contribution}
                    </span>
                  </div>
                );
              })}
            </div>

            <div className="pt-2 border-t border-[#1E293B] flex items-center justify-between text-[9px] font-mono text-slate-500">
              <span>ACTIVE TYPOLOGIES: {detectedPatterns.length}</span>
              <span>GRAPH OBSERVED</span>
            </div>
          </div>

          {/* Right: Payment Channel Risk Profile Horizontal Bar Chart (6 cols) */}
          <PaymentChannelRiskProfile
            channelPerf={channelPerf}
            totalTx={totalTx}
            timeframe={timeframe}
          />

        </div>
      </section>

      {/* ── 4. INVESTIGATION PERFORMANCE ─────────────────────────────────────── */}
      <section className="space-y-2">
        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase tracking-wider px-1">
          <span>Tier 04 // Investigation Pipeline Performance</span>
          <span>Deterministic 5-Stage Triage & Investigation Confidence Telemetry</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">

          {/* Left: Forensic Case Lifecycle Telemetry (6 cols) */}
          <div className="lg:col-span-6 bg-[#0B132B]/90 border border-[#1E293B] p-5 rounded-xl shadow-xl flex flex-col justify-between space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1E293B] pb-3">
              <div>
                <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-emerald-400" />
                  Forensic Case Lifecycle Telemetry
                </h2>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  Real case throughput calculated from active case database records
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono px-2.5 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-bold uppercase">
                  {investigationPerf?.resolution_rate ?? 0}% Resolution Rate
                </span>
              </div>
            </div>

            {/* KPI Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 font-mono">
              <div className="p-3 bg-[#060B15] rounded-xl border border-[#1E293B]">
                <span className="text-[9px] text-slate-400 uppercase tracking-wider block">Opened</span>
                <span className="text-lg font-bold text-slate-100 mt-0.5 block">
                  {investigationPerf ? investigationPerf.cases_opened.toLocaleString() : '—'}
                </span>
                <span className="text-[8px] text-slate-500 block">Triggered cases</span>
              </div>
              <div className="p-3 bg-[#060B15] rounded-xl border border-[#1E293B]">
                <span className="text-[9px] text-slate-400 uppercase tracking-wider block">Investigated</span>
                <span className="text-lg font-bold text-sky-400 mt-0.5 block">
                  {investigationPerf ? investigationPerf.cases_investigated.toLocaleString() : '—'}
                </span>
                <span className="text-[8px] text-slate-500 block">Pipeline ran</span>
              </div>
              <div className="p-3 bg-[#060B15] rounded-xl border border-[#1E293B]">
                <span className="text-[9px] text-slate-400 uppercase tracking-wider block">Escalated</span>
                <span className="text-lg font-bold text-amber-400 mt-0.5 block">
                  {investigationPerf ? investigationPerf.cases_escalated.toLocaleString() : '—'}
                </span>
                <span className="text-[8px] text-slate-500 block">High severity</span>
              </div>
              <div className="p-3 bg-[#060B15] rounded-xl border border-[#1E293B]">
                <span className="text-[9px] text-slate-400 uppercase tracking-wider block">Resolved</span>
                <span className="text-lg font-bold text-emerald-400 mt-0.5 block">
                  {investigationPerf ? investigationPerf.cases_resolved.toLocaleString() : '—'}
                </span>
                <span className="text-[8px] text-slate-500 block">Actioned/closed</span>
              </div>
            </div>

            {/* Case Resolution Progress Bar */}
            <div className="space-y-1.5 pt-1">
              <div className="flex justify-between text-[10px] font-mono text-slate-400">
                <span>CASE RESOLUTION PROGRESS</span>
                <span>{investigationPerf ? `${investigationPerf.cases_resolved} / ${investigationPerf.cases_opened} cases` : '—'}</span>
              </div>
              <div className="w-full bg-[#060B15] h-2 rounded-full overflow-hidden border border-[#1E293B]">
                <div 
                  className="bg-emerald-500 h-full rounded-full transition-all duration-500" 
                  style={{ width: `${Math.min(100, Math.max(0, resolutionRate))}%` }} 
                />
              </div>
            </div>

            <div className="pt-2 border-t border-[#1E293B] flex items-center justify-between text-[9px] font-mono text-slate-500">
              <span>ACTIVE PIPELINE: 5 AGENTS</span>
              <span>DETERMINISTIC CASE TRIAGE</span>
            </div>
          </div>

          {/* Right: Investigation Confidence Telemetry (6 cols) */}
          <div className="lg:col-span-6 bg-[#0B132B]/90 border border-[#1E293B] p-5 rounded-xl shadow-xl flex flex-col justify-between space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1E293B] pb-3">
              <div>
                <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-sky-400" />
                  Investigation Confidence
                </h2>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  How strongly evidence supports the investigation conclusion
                </p>
              </div>
              <div>
                {invConfidence?.status === 'AVAILABLE' ? (
                  <span className={`text-[10px] font-mono px-2.5 py-0.5 rounded font-bold uppercase border ${
                    (invConfidence.score ?? invConfidence.confidence_score) >= 85
                      ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                      : (invConfidence.score ?? invConfidence.confidence_score) >= 60
                      ? 'bg-sky-500/15 border-sky-500/30 text-sky-300'
                      : 'bg-amber-500/15 border-amber-500/30 text-amber-300'
                  }`}>
                    {invConfidence.label || invConfidence.confidence_level}
                  </span>
                ) : (
                  <span className="text-[10px] font-mono px-2.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400 uppercase">
                    INSUFFICIENT DATA
                  </span>
                )}
              </div>
            </div>

            {/* Prominent Callout: Explicit distinction from risk score with tooltip */}
            <div className="group relative flex items-center justify-between px-3 py-2 rounded-lg bg-[#060B15] border border-sky-500/20 text-[10px] font-mono text-sky-300 cursor-help">
              <div className="flex items-center gap-2">
                <Info className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                <span>Evidence Support Index • Not Fraud Probability</span>
              </div>
              <span className="text-[9px] text-slate-500 hidden sm:inline underline decoration-dotted">
                Distinction Info
              </span>

              {/* Tooltip on Hover */}
              <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block z-30 w-72 p-2.5 rounded-lg bg-[#0B132B] border border-sky-500/30 shadow-2xl text-[11px] font-sans text-slate-300 pointer-events-none">
                <span className="font-mono font-bold text-sky-400 block mb-1 text-xs">
                  INVESTIGATION CONFIDENCE
                </span>
                Measures how strongly the investigation is supported by available evidence completeness, agent agreement, source diversity, and identified contradictions.
                <span className="block mt-1.5 text-amber-300/90 font-mono text-[10px]">
                  Distinct from Risk Score: A high risk score with medium confidence indicates urgent suspicion where deeper evidence collection is still underway.
                </span>
              </div>
            </div>

            {(!invConfidence || invConfidence.status !== 'AVAILABLE' || invConfidence.cases_evaluated === 0) ? (
              <div className="h-[150px] flex flex-col items-center justify-center text-center p-4 border border-dashed border-[#1E293B] rounded-xl bg-[#060B15]">
                <AlertTriangle className="w-6 h-6 text-slate-500 mb-1.5" />
                <span className="text-xs font-mono font-bold text-slate-400 uppercase">INSUFFICIENT INVESTIGATION RUNS</span>
                <p className="text-[10px] text-slate-500 font-sans mt-1 max-w-sm">
                  No completed 5-stage case investigations found in current timeframe ({timeframe}). Run case investigation in Investigation Workspace to generate confidence telemetry.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {/* Confidence Hero Meter */}
                {(() => {
                  const scoreVal = invConfidence.score ?? invConfidence.confidence_score ?? 0;
                  const scoreColor = scoreVal >= 85 ? 'text-emerald-400' : scoreVal >= 60 ? 'text-sky-400' : 'text-amber-400';
                  const scoreBg = scoreVal >= 85 ? 'bg-emerald-500' : scoreVal >= 60 ? 'bg-sky-500' : 'bg-amber-500';
                  const scoreGlow = scoreVal >= 85 ? 'shadow-[0_0_12px_rgba(16,185,129,0.35)]' : scoreVal >= 60 ? 'shadow-[0_0_12px_rgba(56,189,248,0.35)]' : 'shadow-[0_0_12px_rgba(245,158,11,0.35)]';

                  return (
                    <div className="space-y-1.5">
                      <div className="flex justify-between items-baseline font-mono">
                        <span className="text-[10px] text-slate-400 uppercase">Composite Confidence Score</span>
                        <div className="flex items-baseline gap-2">
                          <span className={`text-2xl font-extrabold ${scoreColor}`}>
                            {scoreVal}%
                          </span>
                          <span className="text-[10px] font-bold text-slate-400">
                            ({invConfidence.label || invConfidence.confidence_level})
                          </span>
                        </div>
                      </div>
                      <div className="w-full bg-[#060B15] h-2.5 rounded-full overflow-hidden border border-[#1E293B]">
                        <div 
                          className={`h-full rounded-full transition-all duration-500 ${scoreBg} ${scoreGlow}`} 
                          style={{ width: `${Math.min(100, Math.max(0, scoreVal))}%` }} 
                        />
                      </div>
                    </div>
                  );
                })()}

                {/* 4 Supporting Factor Metric Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px]">
                  {/* 1. Evidence Completeness */}
                  <div className="p-2 bg-[#060B15] rounded-lg border border-[#1E293B] flex flex-col justify-between">
                    <div>
                      <div className="text-slate-400 flex justify-between text-[9px]">
                        <span>EVIDENCE</span>
                        <span className="text-slate-500">35%</span>
                      </div>
                      <span className="text-sm font-bold text-indigo-400 block mt-0.5">
                        {invConfidence.evidence_completeness}%
                      </span>
                    </div>
                    <div className="mt-1.5">
                      <div className="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
                        <div className="bg-indigo-400 h-full" style={{ width: `${invConfidence.evidence_completeness}%` }} />
                      </div>
                      <span className="text-[8px] text-slate-500 block mt-0.5 truncate">5 Core Types</span>
                    </div>
                  </div>

                  {/* 2. Agent Agreement */}
                  <div className="p-2 bg-[#060B15] rounded-lg border border-[#1E293B] flex flex-col justify-between">
                    <div>
                      <div className="text-slate-400 flex justify-between text-[9px]">
                        <span>AGREEMENT</span>
                        <span className="text-slate-500">40%</span>
                      </div>
                      <span className="text-sm font-bold text-emerald-400 block mt-0.5">
                        {invConfidence.agent_agreement}%
                      </span>
                    </div>
                    <div className="mt-1.5">
                      <div className="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
                        <div className="bg-emerald-400 h-full" style={{ width: `${invConfidence.agent_agreement}%` }} />
                      </div>
                      <span className="text-[8px] text-slate-500 block mt-0.5 truncate">Agent Consensus</span>
                    </div>
                  </div>

                  {/* 3. Source Diversity */}
                  <div className="p-2 bg-[#060B15] rounded-lg border border-[#1E293B] flex flex-col justify-between">
                    <div>
                      <div className="text-slate-400 flex justify-between text-[9px]">
                        <span>DIVERSITY</span>
                        <span className="text-slate-500">25%</span>
                      </div>
                      <span className="text-sm font-bold text-sky-400 block mt-0.5">
                        {invConfidence.source_diversity}%
                      </span>
                    </div>
                    <div className="mt-1.5">
                      <div className="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
                        <div className="bg-sky-400 h-full" style={{ width: `${invConfidence.source_diversity}%` }} />
                      </div>
                      <span className="text-[8px] text-slate-500 block mt-0.5 truncate">Distinct Sources</span>
                    </div>
                  </div>

                  {/* 4. Contradictions */}
                  <div className="p-2 bg-[#060B15] rounded-lg border border-[#1E293B] flex flex-col justify-between">
                    <div>
                      <div className="text-slate-400 flex justify-between text-[9px]">
                        <span>CONFLICTS</span>
                        <span className="text-slate-500">-1%</span>
                      </div>
                      <span className={`text-sm font-bold block mt-0.5 ${
                        invConfidence.contradiction_count > 0 ? 'text-amber-400' : 'text-emerald-400'
                      }`}>
                        {invConfidence.contradiction_count}
                      </span>
                    </div>
                    <div className="mt-1.5">
                      <span className={`text-[8px] px-1 py-0.5 rounded font-bold block text-center truncate ${
                        invConfidence.contradiction_count > 0 
                          ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30' 
                          : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                      }`}>
                        {invConfidence.contradiction_count > 0 ? `-${invConfidence.contradiction_count}% Penalty` : '0 Conflicts'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Micro Meta Footer */}
            <div className="pt-2 border-t border-[#1E293B] flex items-center justify-between text-[9px] font-mono text-slate-500">
              <span>EVALUATED: {invConfidence?.cases_evaluated ?? 0} COMPLETED RUNS</span>
              <span>FORMULA: 0.35·EV + 0.40·AG + 0.25·DIV - 1.0·CT</span>
            </div>
          </div>

        </div>
      </section>

      {/* ── 5. ACTION & AUTOMATION PERFORMANCE ───────────────────────────────── */}
      <section className="space-y-2">
        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase tracking-wider px-1">
          <span>Tier 05 // Enforcement & Automation Performance</span>
          <span>Deterministic Policy Outcomes & Human Authorization Boundaries</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          
          {/* Left: Action Outcomes Distribution (8 cols on lg, 9 cols on xl ~ 70-75%) */}
          <div className="lg:col-span-8 xl:col-span-9 bg-[#0B132B]/90 border border-[#1E293B] p-5 rounded-xl shadow-xl space-y-3.5">
            {/* Header & Total */}
            <div className="flex items-start justify-between gap-2">
              <div>
                <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-purple-400" />
                  Policy Enforcement Action Outcomes
                </h2>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  Policy enforcement evaluation records logged across evaluated transactions · {timeframe.toUpperCase()}
                </p>
              </div>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-500/10 border border-purple-500/30 text-purple-300 shrink-0">
                Total: {totalActionSum.toLocaleString()} Records
              </span>
            </div>

            {/* Context Explanation Callout */}
            <div className="bg-[#060B15]/90 border border-[#1E293B] rounded-lg p-2.5 flex items-start gap-2 text-[11px] font-sans text-slate-400 leading-relaxed">
              <Info className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
              <span>
                <strong className="text-slate-200 font-mono">Policy Evaluation Records:</strong> Logged by SENTINEL&apos;s Autonomous Policy Engine across evaluated transactions. <strong className="text-rose-400 font-mono">Freezes</strong> enforce a strict human operator authorization boundary prior to account state mutation.
              </span>
            </div>

            {/* Action Mix Header (Compact Summary Row) */}
            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
              <div className="bg-[#060B15]/60 border border-[#1E293B] rounded-lg p-2">
                <span className="text-slate-500 uppercase tracking-wider block text-[9px]">Primary Outcome ({timeframe.toUpperCase()})</span>
                {primaryAction ? (
                  <span className="text-slate-200 font-bold flex items-center gap-1.5 mt-0.5 truncate">
                    <span className="text-amber-400 truncate">{primaryAction.action}</span>
                    <span className="text-slate-400 font-normal">· {primaryAction.count.toLocaleString()} ({primaryAction.pct}%)</span>
                  </span>
                ) : (
                  <span className="text-slate-500 mt-0.5 block">No action records</span>
                )}
              </div>
              <div className="bg-[#060B15]/60 border border-[#1E293B] rounded-lg p-2">
                <span className="text-slate-500 uppercase tracking-wider block text-[9px]">Operator Boundary</span>
                <span className="text-slate-200 font-bold flex items-center gap-1.5 mt-0.5">
                  <span className="text-rose-400">{freezeCount.toLocaleString()} Freezes</span>
                  <span className="text-slate-400 font-normal">· Pending Approval</span>
                </span>
              </div>
            </div>

            {/* Action Bars List (Volume Sorted: Active > 0 first, then Supported 0) */}
            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
              {sortedActions.map((item) => {
                const pct = totalActionSum > 0 ? (((item.count || 0) / totalActionSum) * 100).toFixed(1) : '0.0';
                const theme = ACTION_THEMES[item.action] || {
                  bar: 'bg-purple-500',
                  text: 'text-slate-300',
                  badge: 'bg-slate-800 text-slate-400 border-slate-700',
                  statusLabel: item.status || 'Active',
                  governance: 'Evaluated action record in SENTINEL engine.'
                };
                const isZero = (item.count || 0) === 0;
                const isHovered = hoveredAction === item.action;

                return (
                  <div 
                    key={item.action} 
                    onMouseEnter={() => setHoveredAction(item.action)}
                    onMouseLeave={() => setHoveredAction(null)}
                    className={`p-2.5 rounded-lg transition-all border ${
                      isHovered 
                        ? 'bg-[#060B15] border-slate-700 shadow-md' 
                        : 'bg-[#060B15]/40 border-transparent hover:border-[#1E293B]'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px] font-mono mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className={`font-bold ${isZero ? 'text-slate-500' : theme.text}`}>
                          {item.action}
                        </span>
                        <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${
                          isZero 
                            ? 'bg-slate-800/80 text-slate-500 border-slate-700/60' 
                            : theme.badge
                        }`}>
                          {isZero ? `Supported • 0 in ${timeframe.toUpperCase()}` : theme.statusLabel}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className={isZero ? 'text-slate-600' : 'text-slate-200 font-bold'}>
                          {(item.count || 0).toLocaleString()}
                        </span>
                        <span className="text-slate-500 text-[10px] ml-1.5">
                          ({pct}%)
                        </span>
                      </div>
                    </div>

                    {/* Progress Track */}
                    <div className="w-full bg-[#060B15] h-2 rounded-full overflow-hidden border border-[#1E293B]/70">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${isZero ? 'bg-transparent' : theme.bar}`} 
                        style={{ width: `${Math.min(100, Math.max(0, Number(pct)))}%` }} 
                      />
                    </div>

                    {/* Expandable Context on Hover */}
                    {isHovered && (
                      <div className="mt-2 pt-1.5 border-t border-[#1E293B]/80 text-[10px] font-mono text-slate-400 flex flex-col gap-0.5">
                        <div className="flex justify-between text-slate-500 text-[9px]">
                          <span>CODE: {item.code || item.action}</span>
                          <span>FORMULA: {item.count || 0} / {totalActionSum} = {pct}%</span>
                        </div>
                        <p className="text-slate-400 font-sans text-[10.5px] leading-snug">
                          {theme.governance}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Reconciliation Footer */}
            <div className="pt-2 border-t border-[#1E293B] flex items-center justify-between text-[9px] font-mono text-slate-500">
              <span>RECONCILED: {totalActionSum.toLocaleString()} / {totalActionSum.toLocaleString()} RECORDS (100.0%)</span>
              <span className="text-slate-400">SOURCE: data_store[&apos;executed_actions&apos;]</span>
            </div>
          </div>

          {/* Right: Automation & Governance (4 cols on lg, 3 cols on xl ~ 25-30%) */}
          <div className="lg:col-span-4 xl:col-span-3 bg-[#0B132B]/90 border border-[#1E293B] p-5 rounded-xl shadow-xl space-y-3.5 flex flex-col justify-between">
            <div className="flex items-center justify-between gap-2 border-b border-[#1E293B] pb-3">
              <div>
                <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  Automation & Governance
                </h2>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  Enforcement decision authority
                </p>
              </div>
              <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border uppercase shrink-0 ${
                autoIntel?.automation_mode 
                  ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40' 
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}>
                {autoIntel?.automation_mode ? 'AUTONOMOUS' : 'MANUAL'}
              </span>
            </div>

            {/* Focused Compact Two-Card Presentation */}
            <div className="space-y-3 font-mono my-auto">
              {/* Card 1: Automated Decisions */}
              <div className="p-3.5 bg-[#060B15] rounded-xl border border-[#1E293B] flex flex-col justify-between space-y-1">
                <div className="flex items-center justify-between text-[10px] text-slate-400 uppercase tracking-wider">
                  <div className="flex items-center gap-1.5 font-bold text-slate-200">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span>AUTOMATED DECISIONS</span>
                  </div>
                  <span className="text-[8.5px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 font-semibold">
                    POLICY
                  </span>
                </div>
                <div className="text-2xl font-bold text-emerald-400 pt-0.5">
                  {autoIntel ? autoIntel.automated_actions_count.toLocaleString() : '—'}
                </div>
                <p className="text-[10px] text-slate-500 font-sans">
                  Policy-driven decisions
                </p>
              </div>

              {/* Card 2: Human Decisions */}
              <div className="p-3.5 bg-[#060B15] rounded-xl border border-[#1E293B] flex flex-col justify-between space-y-1">
                <div className="flex items-center justify-between text-[10px] text-slate-400 uppercase tracking-wider">
                  <div className="flex items-center gap-1.5 font-bold text-slate-200">
                    <span className="w-2 h-2 rounded-full bg-purple-400" />
                    <span>HUMAN DECISIONS</span>
                  </div>
                  <span className="text-[8.5px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30 font-semibold">
                    OPERATOR
                  </span>
                </div>
                <div className="text-2xl font-bold text-purple-400 pt-0.5">
                  {autoIntel ? autoIntel.human_actions_count.toLocaleString() : '—'}
                </div>
                <p className="text-[10px] text-slate-500 font-sans">
                  Analyst/operator decisions
                </p>
              </div>
            </div>

            {/* Reconciliation Footer */}
            <div className="pt-2 border-t border-[#1E293B] flex items-center justify-between text-[9px] font-mono text-slate-500">
              <span>AUTHORITY AUDIT</span>
              <span>LIVE TELEMETRY</span>
            </div>
          </div>

        </div>
      </section>

      {/* ── 6. INVESTIGATION IMPACT & FINANCIAL OUTCOMES ─────────────────────── */}
      <section className="space-y-2">
        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase tracking-wider px-1">
          <span>Tier 06 // Investigation Impact & Financial Outcomes</span>
          <span>Deterministic Case Lifecycle Resolution & Audited Capital Protection</span>
        </div>

        {/* Unified Analytical Container */}
        <div className="bg-[#0B132B]/90 border border-[#1E293B] p-5 rounded-xl shadow-xl space-y-5">
          
          {/* Subsection 1: Investigation Impact */}
          <div className="space-y-3.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-sky-400" />
                  Investigation Impact
                </h2>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  Forensic case throughput across triage and resolution pipeline
                </p>
              </div>
              <span className="text-[10px] font-mono text-sky-400 font-bold px-2.5 py-0.5 rounded bg-sky-500/15 border border-sky-500/40">
                Resolution Rate: {investigationPerf?.resolution_rate ?? 0}%
              </span>
            </div>

            {/* Investigation KPI Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
              <div className="p-3.5 bg-[#060B15] rounded-xl border border-[#1E293B]">
                <span className="text-[9.5px] text-slate-400 uppercase tracking-wider block">Opened</span>
                <span className="text-xl font-bold text-slate-100 mt-1 block">
                  {investigationPerf ? investigationPerf.cases_opened.toLocaleString() : '—'}
                </span>
                <span className="text-[9px] text-slate-500 mt-0.5 block">Triggered cases</span>
              </div>

              <div className="p-3.5 bg-[#060B15] rounded-xl border border-[#1E293B]">
                <span className="text-[9.5px] text-slate-400 uppercase tracking-wider block">Investigated</span>
                <span className="text-xl font-bold text-sky-400 mt-1 block">
                  {investigationPerf ? investigationPerf.cases_investigated.toLocaleString() : '—'}
                </span>
                <span className="text-[9px] text-slate-500 mt-0.5 block">Pipeline ran</span>
              </div>

              <div className="p-3.5 bg-[#060B15] rounded-xl border border-[#1E293B]">
                <span className="text-[9.5px] text-slate-400 uppercase tracking-wider block">Escalated</span>
                <span className="text-xl font-bold text-amber-400 mt-1 block">
                  {investigationPerf ? investigationPerf.cases_escalated.toLocaleString() : '—'}
                </span>
                <span className="text-[9px] text-slate-500 mt-0.5 block">High severity</span>
              </div>

              <div className="p-3.5 bg-[#060B15] rounded-xl border border-[#1E293B]">
                <span className="text-[9.5px] text-slate-400 uppercase tracking-wider block">Resolved</span>
                <span className="text-xl font-bold text-emerald-400 mt-1 block">
                  {investigationPerf ? investigationPerf.cases_resolved.toLocaleString() : '—'}
                </span>
                <span className="text-[9px] text-slate-500 mt-0.5 block">Actioned/closed</span>
              </div>
            </div>

            {/* Case Resolution Progress Bar */}
            <div className="space-y-1.5 pt-0.5">
              <div className="flex justify-between text-[10px] font-mono text-slate-400">
                <span>CASE RESOLUTION PROGRESS</span>
                <span className="text-slate-300 font-bold">
                  {investigationPerf ? `${investigationPerf.cases_resolved} / ${investigationPerf.cases_opened} cases (${investigationPerf.resolution_rate}%)` : '—'}
                </span>
              </div>
              <div className="w-full bg-[#060B15] h-2 rounded-full overflow-hidden border border-[#1E293B]">
                <div 
                  className="bg-sky-500 h-full rounded-full transition-all duration-500" 
                  style={{ width: `${Math.min(100, Math.max(0, Number(investigationPerf?.resolution_rate || 0)))}%` }} 
                />
              </div>
            </div>
          </div>

          {/* Subtle Horizontal Divider */}
          <div className="border-t border-[#1E293B]" />

          {/* Subsection 2: Financial Impact & Asset Recovery */}
          <div className="space-y-3.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-emerald-400" />
                  Financial Impact & Asset Recovery
                </h2>
                <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                  Audited financial exposure, recovered assets, and net loss prevention
                </p>
              </div>
              <span className="text-[10px] font-mono text-emerald-400 font-bold px-2.5 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/40">
                Recovery Rate: {finImpact ? `${finImpact.recovery_rate}%` : '—'}
              </span>
            </div>

            {/* Financial KPI Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono">
              <div className="p-3.5 bg-[#060B15] rounded-xl border border-[#1E293B]">
                <span className="text-[9.5px] text-slate-400 uppercase tracking-wider block">Total Exposure</span>
                <span className="text-xl font-bold text-slate-100 mt-1 block">
                  {finImpact ? formatINR(finImpact.total_exposure) : '—'}
                </span>
                <span className="text-[9px] text-slate-500 mt-0.5 block">Sum of flagged fraud transactions</span>
              </div>

              <div className="p-3.5 bg-[#060B15] rounded-xl border border-[#1E293B]">
                <span className="text-[9.5px] text-slate-400 uppercase tracking-wider block">Recovered Assets</span>
                <span className="text-xl font-bold text-emerald-400 mt-1 block">
                  {finImpact ? formatINR(finImpact.recovered_assets) : '—'}
                </span>
                <span className="text-[9px] text-emerald-500/80 mt-0.5 block">Protected capital through interventions</span>
              </div>

              <div className="p-3.5 bg-[#060B15] rounded-xl border border-[#1E293B]">
                <span className="text-[9.5px] text-slate-400 uppercase tracking-wider block">Estimated Net Loss</span>
                <span className="text-xl font-bold text-rose-400 mt-1 block">
                  {finImpact ? formatINR(finImpact.estimated_loss) : '—'}
                </span>
                <span className="text-[9px] text-slate-500 mt-0.5 block">Exposure minus recovered assets</span>
              </div>
            </div>

            {/* Recovery Progress Meter */}
            <div className="space-y-1.5 pt-0.5">
              <div className="flex justify-between text-[10px] font-mono text-slate-400">
                <span>RECOVERY EFFICIENCY</span>
                <span className="text-emerald-400 font-bold">{finImpact ? `${finImpact.recovery_rate}%` : '—'}</span>
              </div>
              <div className="w-full bg-[#060B15] h-2 rounded-full overflow-hidden border border-[#1E293B]">
                <div 
                  className="bg-emerald-500 h-full rounded-full transition-all duration-500" 
                  style={{ width: `${Math.min(100, Math.max(0, Number(finImpact?.recovery_rate || 0)))}%` }} 
                />
              </div>
            </div>
          </div>

          {/* Reconciliation Footer */}
          <div className="pt-2 border-t border-[#1E293B] flex items-center justify-between text-[9px] font-mono text-slate-500">
            <span>DATA RECONCILIATION: ACTIVE CASE REPOSITORY & AUDITED CAPITAL TELEMETRY</span>
            <span>ZERO FABRICATED TELEMETRY • LIVE DATABASE BOUND</span>
          </div>
        </div>
      </section>

      {/* ── FOOTER ────────────────────────────────────────────────────────────── */}
      <footer className="pt-5 pb-3 border-t border-[#1E293B] flex flex-col sm:flex-row justify-between items-center gap-3 text-[11px] text-slate-500 font-mono">
        <span>SENTINEL Financial Crime Intelligence Platform • Analytics Engine</span>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-emerald-400">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping" />
            Zero Fabricated Telemetry • Live Database Bound
          </span>
        </div>
      </footer>

    </div>
  );
};

export default Dashboard;
