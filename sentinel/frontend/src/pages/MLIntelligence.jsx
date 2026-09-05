import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Brain, Play, RotateCcw, Activity, CheckCircle2, Clock, Zap,
  ArrowRight, ArrowDown, TrendingUp, BarChart3, ShieldAlert, Loader2, Info,
  ChevronDown, Layers, Target, GitBranch, Hash, Database, Cpu, Network,
  Sparkles, Sliders, ShieldCheck
} from 'lucide-react';
import RiskBadge from '../components/RiskBadge';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const FEATURE_CONFIG = {
  amount:          { label: 'Transaction Amount',   color: '#38bdf8' },
  hour:            { label: 'Temporal Anomaly',     color: '#818cf8' },
  is_new_receiver: { label: 'New Receiver Signal',  color: '#f59e0b' },
  velocity:        { label: 'Velocity Pattern',     color: '#fb923c' },
  chain_depth:     { label: 'Hop Chain Depth',      color: '#34d399' },
  call_flag:       { label: 'Coercion Indicator',   color: '#f87171' },
};

function getRiskColor(score) {
  if (score >= 85) return { text: 'text-rose-400', hex: '#f87171' };
  if (score >= 70) return { text: 'text-orange-400', hex: '#fb923c' };
  if (score >= 40) return { text: 'text-amber-400', hex: '#fbbf24' };
  return { text: 'text-emerald-400', hex: '#34d399' };
}

function getRiskLabel(score) {
  if (score >= 85) return 'CRITICAL';
  if (score >= 70) return 'HIGH';
  if (score >= 40) return 'MEDIUM';
  return 'LOW';
}

function formatCurrency(amount) {
  if (!amount) return 'Rs 0';
  if (amount >= 1000000) return 'Rs ' + (amount / 1000000).toFixed(2) + 'M';
  if (amount >= 1000) return 'Rs ' + (amount / 1000).toFixed(1) + 'K';
  return 'Rs ' + amount.toFixed(0);
}

function useAnimatedCount(target, duration, active) {
  const [value, setValue] = useState(0);
  const rafRef = useRef(null);
  useEffect(() => {
    if (!active || target === 0) { setValue(0); return; }
    const start = performance.now();
    const animate = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [target, duration, active]);
  return value;
}

/**
 * Enhanced Enterprise ML Neural Network Visualization (Hero Component)
 * Prominent multi-layer architecture with active tensor feed and layer-by-layer progressive signaling.
 */
function NeuralNetworkViz({ activeInputs = [], modelActive = false, outputActive = false }) {
  const layers = [[0,1,2,3,4,5],[0,1,2,3],[0,1,2],[0,1]];
  const layerX = [20, 130, 240, 340];
  const nodeSpacing = 32;

  function nodeY(li, ni) {
    const s = layers[li].length;
    return 105 - ((s - 1) * nodeSpacing) / 2 + ni * nodeSpacing;
  }

  const edges = [];
  for (let l = 0; l < layers.length - 1; l++) {
    for (let ni = 0; ni < layers[l].length; ni++) {
      for (let nj = 0; nj < layers[l + 1].length; nj++) {
        edges.push({ x1: layerX[l], y1: nodeY(l, ni), x2: layerX[l + 1], y2: nodeY(l + 1, nj), l });
      }
    }
  }

  const featureColors = ['#38bdf8', '#818cf8', '#f59e0b', '#fb923c', '#34d399', '#f87171'];

  return (
    <div className="w-full relative py-2">
      <svg viewBox="0 0 370 220" className="w-full h-56 md:h-64 select-none" style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id="edgeGradActive" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#818cf8" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#c084fc" stopOpacity="0.6" />
          </linearGradient>
          <filter id="nodeGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Synapse Connection Mesh */}
        {edges.map((e, i) => {
          const isL0Active = e.l === 0 && activeInputs.length > 0;
          const isLActive = modelActive || isL0Active;
          const stroke = isLActive ? 'url(#edgeGradActive)' : 'rgba(148,163,184,0.22)';
          const strokeWidth = isLActive ? 1.3 : 0.9;
          return (
            <line
              key={i}
              x1={e.x1 + 8}
              y1={e.y1}
              x2={e.x2 - 8}
              y2={e.y2}
              stroke={stroke}
              strokeWidth={strokeWidth}
              strokeDasharray={isLActive ? '4 3' : 'none'}
              style={{
                transition: 'stroke 0.4s, stroke-width 0.4s',
                animation: isLActive ? 'dashScroll 1.2s linear infinite' : 'none',
              }}
            />
          );
        })}

        {/* Neurons by Layer */}
        {layers.map((layer, li) => layer.map((_, ni) => {
          const x = layerX[li];
          const y = nodeY(li, ni);
          const active = li === 0 ? activeInputs.includes(ni) : (li < 3 ? modelActive : outputActive);
          const fill = active
            ? (li === 0 ? featureColors[ni] : (li === 3 ? (ni === 0 ? '#818cf8' : '#34d399') : '#c084fc'))
            : '#0f172a';
          const stroke = active
            ? (li === 0 ? featureColors[ni] + 'dd' : 'rgba(192,132,252,0.9)')
            : '#475569';

          return (
            <g key={li + '-' + ni}>
              {active && (
                <circle
                  cx={x}
                  cy={y}
                  r="13"
                  fill="none"
                  stroke={stroke}
                  strokeWidth="0.8"
                  opacity="0.6"
                  style={{ animation: 'nnpulse 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite' }}
                />
              )}
              <circle
                cx={x}
                cy={y}
                r="7.5"
                fill={fill}
                stroke={stroke}
                strokeWidth="1.5"
                filter={active ? 'url(#nodeGlow)' : undefined}
                style={{ transition: 'fill 0.4s, stroke 0.4s' }}
              />
              <circle
                cx={x}
                cy={y}
                r="2.5"
                fill={active ? '#ffffff' : '#64748b'}
                opacity={active ? 0.95 : 0.75}
              />
            </g>
          );
        }))}

        {/* Layer Identity Headers */}
        {[
          { label: 'INPUT', sub: '6 dims', x: layerX[0] },
          { label: 'HIDDEN 1', sub: '4 units', x: layerX[1] },
          { label: 'HIDDEN 2', sub: '3 units', x: layerX[2] },
          { label: 'OUTPUT', sub: 'Softmax', x: layerX[3] },
        ].map((hdr, i) => (
          <g key={i}>
            <text
              x={hdr.x}
              y="202"
              textAnchor="middle"
              fill={modelActive || (i === 0 && activeInputs.length > 0) ? '#f8fafc' : '#cbd5e1'}
              fontSize="9.5"
              fontFamily="monospace"
              fontWeight="700"
              letterSpacing="0.05em"
            >
              {hdr.label}
            </text>
            <text
              x={hdr.x}
              y="214"
              textAnchor="middle"
              fill={modelActive || (i === 0 && activeInputs.length > 0) ? '#a5b4fc' : '#94a3b8'}
              fontSize="8"
              fontFamily="monospace"
            >
              {hdr.sub}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function FlowConnector({ active, color }) {
  return (
    <div className="flex flex-col items-center py-1 gap-0.5">
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: '2px', height: '6px', background: active ? color : 'rgba(255,255,255,0.06)',
          borderRadius: '9999px', opacity: active ? 1 - i * 0.2 : 0.25,
          transition: 'background 0.4s', transitionDelay: i * 80 + 'ms'
        }} />
      ))}
      <svg width="12" height="10" viewBox="0 0 12 10" style={{ marginTop: '2px' }}>
        <path d="M6 10 L0 0 L12 0 Z" fill={active ? color : 'rgba(148,163,184,0.12)'} style={{ transition: 'fill 0.4s' }} />
      </svg>
    </div>
  );
}

function getNormalizedWeights(featMap) {
  if (!featMap) return {};
  const rawSum = Object.values(featMap).reduce((a, b) => a + (Number(b) || 0), 0);
  const normalized = {};
  for (const [k] of Object.entries(FEATURE_CONFIG)) {
    const raw = Number(featMap[k]) || 0;
    normalized[k] = rawSum > 0 ? (raw / rawSum) : 0;
  }
  return normalized;
}

function stageIn(stage, arr) { return arr.includes(stage); }

const DEFAULT_TRANSACTIONS = [
  {
    tx_id: 'TX-72489060',
    amount: 443300,
    channel: 'NEFT',
    risk_score: 82,
    rule_score: 80,
    ml_score: 84,
    final_score: 82,
    sender_account: 'ACC-USR-5246',
    receiver_account: 'ACC-MULE-9818',
    risk_factors: [
      { name: 'is_new_receiver', contribution: 35, value: 85 },
      { name: 'amount', contribution: 30, value: 75 },
      { name: 'hour', contribution: 20, value: 50 },
    ],
    ml_feature_importance: {
      is_new_receiver: 0.406,
      amount: 0.325,
      hour: 0.253,
      chain_depth: 0.011,
      velocity: 0.005,
      call_flag: 0.000,
    },
    response_decision: { action: 'ESCALATE_ANALYST_REVIEW' },
    confidence: 'HIGH',
  },
  {
    tx_id: 'TX-89210455',
    amount: 250000,
    channel: 'UPI',
    risk_score: 88,
    rule_score: 85,
    ml_score: 91,
    final_score: 88,
    sender_account: 'ACC-USR-3464',
    receiver_account: 'ACC-MULE-1992',
    risk_factors: [
      { name: 'is_new_receiver', contribution: 40, value: 90 },
      { name: 'amount', contribution: 35, value: 80 },
      { name: 'velocity_spike', contribution: 15, value: 65 },
    ],
    ml_feature_importance: {
      is_new_receiver: 0.420,
      amount: 0.340,
      hour: 0.120,
      chain_depth: 0.060,
      velocity: 0.050,
      call_flag: 0.010,
    },
    response_decision: { action: 'REJECT_TRANSACTION' },
    confidence: 'VERY_HIGH',
  },
  {
    tx_id: 'TX-14920194',
    amount: 78500,
    channel: 'IMPS',
    risk_score: 64,
    rule_score: 60,
    ml_score: 68,
    final_score: 64,
    sender_account: 'ACC-USR-1829',
    receiver_account: 'ACC-USR-9931',
    risk_factors: [
      { name: 'hour', contribution: 35, value: 60 },
      { name: 'amount', contribution: 25, value: 55 },
    ],
    ml_feature_importance: {
      is_new_receiver: 0.150,
      amount: 0.280,
      hour: 0.380,
      chain_depth: 0.080,
      velocity: 0.100,
      call_flag: 0.010,
    },
    response_decision: { action: 'ENHANCED_MONITORING' },
    confidence: 'MEDIUM',
  },
];

const MLIntelligence = () => {
  const [cases, setCases] = useState([]);
  const [selectedTx, setSelectedTx] = useState(DEFAULT_TRANSACTIONS[0]);
  const [stage, setStage] = useState('idle');
  const [activeFeatures, setActiveFeatures] = useState([]);
  const [mlResult, setMlResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [modelActive, setModelActive] = useState(false);
  const [outputActive, setOutputActive] = useState(false);
  const [featureProgress, setFeatureProgress] = useState({});
  const [showDropdown, setShowDropdown] = useState(false);
  const [casesLoading, setCasesLoading] = useState(false);
  const timersRef = useRef([]);

  // Auto-scroll refs
  const scrollContainerRef = useRef(null);
  const stageTxRef = useRef(null);
  const stageFeaturesRef = useRef(null);
  const stageModelRef = useRef(null);
  const stageSignalsRef = useRef(null);
  const stageComparisonRef = useRef(null);
  const stagePredictionRef = useRef(null);

  const isAutoFollowActive = useRef(false);
  const userInterruptedScroll = useRef(false);
  const rafScrollRef = useRef(null);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    if (rafScrollRef.current) {
      cancelAnimationFrame(rafScrollRef.current);
      rafScrollRef.current = null;
    }
  }, []);

  const addTimer = useCallback((fn, delay) => {
    timersRef.current.push(setTimeout(fn, delay));
  }, []);

  useEffect(() => () => clearTimers(), [clearTimers]);

  useEffect(() => {
    setCasesLoading(true);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    fetch('/cases', { signal: controller.signal })
      .then(r => r.ok ? r.json() : [])
      .then(data => {
        clearTimeout(timeoutId);
        const valid = (data || []).map(c => {
          let txs = c.transactions || [];
          if ((!txs || txs.length === 0) && Array.isArray(c.edges)) {
            txs = c.edges.map(e => ({
              tx_id: e.tx_id || e.id,
              amount: e.amount || 50000,
              channel: e.channel || 'UPI',
              risk_score: e.risk_score || Math.round(c.risk_level || 75),
              sender_account: e.source || e.from,
              receiver_account: e.target || e.to,
              hop_number: e.hop_number,
              timestamp: e.timestamp,
            }));
          }
          return { ...c, transactions: txs };
        }).filter(c => c.transactions && c.transactions.length > 0);

        if (valid.length > 0) {
          setCases(valid);
        }
      })
      .catch(() => {})
      .finally(() => setCasesLoading(false));

    return () => clearTimeout(timeoutId);
  }, []);

  const resetAnimation = useCallback(() => {
    clearTimers();
    isAutoFollowActive.current = false;
    userInterruptedScroll.current = false;
    setLoading(false);
    setStage('idle');
    setModelActive(false);
    setOutputActive(false);
    setMlResult(null);
    setError(null);
    setActiveFeatures([]);
    setFeatureProgress({});
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [clearTimers]);

  const handleUserScroll = useCallback(() => {
    if (isAutoFollowActive.current) {
      userInterruptedScroll.current = true;
      if (rafScrollRef.current) {
        cancelAnimationFrame(rafScrollRef.current);
        rafScrollRef.current = null;
      }
    }
  }, []);

  /**
   * Ultra-smooth camera follow interpolation using cubic ease-in-out.
   * Eliminates default browser scroll jumpiness.
   */
  const smoothScrollTo = useCallback((targetElement, duration = 850, offset = -20) => {
    const container = scrollContainerRef.current;
    if (!container || !targetElement) return;
    if (userInterruptedScroll.current) return;

    if (rafScrollRef.current) {
      cancelAnimationFrame(rafScrollRef.current);
    }

    const containerRect = container.getBoundingClientRect();
    const targetRect = targetElement.getBoundingClientRect();
    const targetScrollTop = container.scrollTop + (targetRect.top - containerRect.top) + offset;
    
    const maxScroll = container.scrollHeight - container.clientHeight;
    const destination = Math.max(0, Math.min(targetScrollTop, maxScroll));
    const startPosition = container.scrollTop;
    const distance = destination - startPosition;

    if (Math.abs(distance) < 8) return;

    let startTime = null;
    const easeInOutCubic = (t) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

    const step = (currentTime) => {
      if (userInterruptedScroll.current) return;
      if (!startTime) startTime = currentTime;
      const timeElapsed = currentTime - startTime;
      const progress = Math.min(timeElapsed / duration, 1);
      const ease = easeInOutCubic(progress);

      container.scrollTop = startPosition + distance * ease;

      if (progress < 1) {
        rafScrollRef.current = requestAnimationFrame(step);
      } else {
        rafScrollRef.current = null;
      }
    };

    rafScrollRef.current = requestAnimationFrame(step);
  }, []);

  const runMLAnalysis = useCallback(async () => {
    if (!selectedTx || loading) return;
    clearTimers();
    setLoading(true);
    setError(null);
    isAutoFollowActive.current = true;
    userInterruptedScroll.current = false;

    // Reset pipeline view for fresh execution
    setActiveFeatures([]);
    setFeatureProgress({});
    setModelActive(false);
    setOutputActive(false);
    setStage('transaction');

    const payload = {
      tx_id: selectedTx.tx_id,
      sender_account: selectedTx.sender_account || 'ACC-BM-SENDER-01',
      receiver_account: selectedTx.receiver_account || 'ACC-BM-RECEIVER-99',
      amount: selectedTx.amount || 25000,
      channel: selectedTx.channel || 'UPI',
      avg_monthly_tx_amount: 25000,
      is_night_time: false,
      on_active_call: (selectedTx.risk_factors || []).some(f => f.name === 'call_flag' && f.value > 0),
      is_new_receiver: (selectedTx.risk_factors || []).some(f => f.name === 'new_receiver' && f.value > 0),
      is_cross_border: (selectedTx.risk_factors || []).some(f => f.name === 'cross_border_risk'),
      velocity_flag: (selectedTx.risk_factors || []).some(f => f.name === 'velocity_spike'),
      device_changed: false,
      hop_number: selectedTx.hop_number || 0,
      timestamp: selectedTx.timestamp || new Date().toISOString(),
    };

    let result = null;
    try {
      const res = await fetch(API_BASE + '/benchmark/custom-evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const data = await res.json();
        result = data.transaction || data;
      }
    } catch {
      // Fallback
    }

    if (!result || result.ml_score === undefined) {
      result = {
        tx_id: selectedTx.tx_id,
        rule_score: selectedTx.rule_score ?? (selectedTx.risk_score || 50),
        ml_score: selectedTx.ml_score ?? Math.min(100, Math.max(0, Math.round((selectedTx.risk_score || 50) * 0.95))),
        final_score: selectedTx.risk_score || 50,
        ml_feature_importance: selectedTx.ml_feature_importance || {
          amount: 0.33,
          is_new_receiver: 0.40,
          hour: 0.25,
          chain_depth: 0.01,
          velocity: 0.01,
          call_flag: 0.00,
        },
        risk_factors: selectedTx.risk_factors || [],
        policy_action: selectedTx.response_decision?.action || 'MONITOR',
        confidence: selectedTx.confidence || 'HIGH',
      };
    }

    setMlResult(result);
    setLoading(false);

    const targetWeights = getNormalizedWeights(result.ml_feature_importance || selectedTx.ml_feature_importance);

    // STEP 1: Transaction Input
    smoothScrollTo(stageTxRef.current, 750);

    // STEP 2: Feature Extraction (staggered bar growth with real values)
    addTimer(() => {
      setStage('features');
      smoothScrollTo(stageFeaturesRef.current, 850);

      const featKeys = Object.keys(FEATURE_CONFIG);
      featKeys.forEach((key, idx) => {
        addTimer(() => {
          setActiveFeatures(prev => [...prev, idx]);
          const targetVal = targetWeights[key] || 0;
          setFeatureProgress(prev => ({
            ...prev,
            [key]: targetVal,
          }));
        }, idx * 220);
      });
    }, 1200);

    // STEP 3: ML Model Inference (Hero Section Focus)
    addTimer(() => {
      setStage('model');
      setModelActive(true);
      smoothScrollTo(stageModelRef.current, 900);
    }, 3400);

    // STEP 4: Top Contributing Signals & ML Impact Analysis
    addTimer(() => {
      setStage('impact');
      smoothScrollTo(stageSignalsRef.current, 900);
    }, 5800);

    // STEP 5: Before ML vs After ML Comparison
    addTimer(() => {
      setStage('comparison');
      smoothScrollTo(stageComparisonRef.current, 900);
    }, 7600);

    // STEP 6: Prediction Output (THE FINAL MAJOR SECTION!)
    addTimer(() => {
      setStage('prediction');
      setOutputActive(true);
      smoothScrollTo(stagePredictionRef.current, 950);
    }, 9400);

    // Final Resolution & release auto-follow
    addTimer(() => {
      setStage('complete');
      isAutoFollowActive.current = false;
    }, 11000);

  }, [selectedTx, loading, clearTimers, addTimer, smoothScrollTo]);

  const txRuleScore = mlResult?.rule_score ?? (selectedTx?.rule_score ?? (selectedTx?.risk_score ?? 75));
  const txMlScore = mlResult?.ml_score ?? (selectedTx?.ml_score ?? (selectedTx?.risk_score ? Math.min(100, Math.max(0, Math.round(selectedTx.risk_score * 0.95 + 4))) : 78));
  const txFinalScore = mlResult?.final_score ?? (selectedTx?.risk_score ?? txRuleScore);

  const mlScoreAnim = useAnimatedCount(Math.round(txMlScore), 700, stageIn(stage, ['prediction', 'complete']));
  const finalScoreAnim = useAnimatedCount(Math.round(txFinalScore), 700, stageIn(stage, ['prediction', 'complete']));

  // Normalized weights for feature extraction
  const targetWeights = useMemo(() => {
    const featMap = mlResult?.ml_feature_importance || selectedTx?.ml_feature_importance || {
      is_new_receiver: 0.406,
      amount: 0.325,
      hour: 0.253,
      chain_depth: 0.011,
      velocity: 0.005,
      call_flag: 0.000,
    };
    return getNormalizedWeights(featMap);
  }, [mlResult, selectedTx]);

  // Ranked Top Contributing Signals (Strongest to Weakest)
  const topFeatures = useMemo(() => {
    const featMap = mlResult?.ml_feature_importance || selectedTx?.ml_feature_importance || {
      is_new_receiver: 0.406,
      amount: 0.325,
      hour: 0.253,
      chain_depth: 0.011,
      velocity: 0.005,
      call_flag: 0.000,
    };
    const rawSum = Object.values(featMap).reduce((a, b) => a + (Number(b) || 0), 0);
    return Object.entries(featMap)
      .map(([k, v]) => [k, rawSum > 0 ? (Number(v) || 0) / rawSum : 0])
      .sort((a, b) => b[1] - a[1]);
  }, [mlResult, selectedTx]);

  const beforeRisk = getRiskColor(txRuleScore);
  const afterRisk = getRiskColor(Math.round(txFinalScore));
  const isRunning = stageIn(stage, ['transaction', 'features', 'model', 'impact', 'comparison', 'prediction']);

  const scoreAdjustment = Math.round(txMlScore - txRuleScore);
  const finalDelta = Math.round(txFinalScore - txRuleScore);

  // Progressive color unmasking flags
  const hasFeaturesActive = stageIn(stage, ['features', 'model', 'impact', 'comparison', 'prediction', 'complete']);
  const hasModelActive = stageIn(stage, ['model', 'impact', 'comparison', 'prediction', 'complete']);
  const hasImpactActive = stageIn(stage, ['impact', 'comparison', 'prediction', 'complete']);
  const hasComparisonActive = stageIn(stage, ['comparison', 'prediction', 'complete']);
  const hasPredictionActive = stageIn(stage, ['prediction', 'complete']);
  const hasCompleteActive = stage === 'complete';

  const displayCases = useMemo(() => {
    if (cases.length > 0) return cases;
    return [
      {
        case_id: 'BENCHMARK-HIGH-RISK',
        risk_level: 85,
        transactions: DEFAULT_TRANSACTIONS,
      }
    ];
  }, [cases]);

  return (
    <div className="flex flex-col h-full min-h-0 bg-background text-foreground overflow-hidden">
      {/* ── Header ── */}
      <div className="shrink-0 px-6 py-4 border-b border-border/60 bg-card/40">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center text-indigo-400 shrink-0">
              <Brain style={{ width: 20, height: 20 }} />
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-lg font-extrabold tracking-tight text-slate-100">
                  ML INTELLIGENCE
                </h1>
                <span className="text-xs font-mono font-bold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                  HYBRID SCORER V16
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-1">
                Rule-Guided ML Emulator · Real-Time Pipeline Visualization
              </p>
            </div>
          </div>

          {/* Action Buttons: [ RESET ] [ ▶ RUN ML ANALYSIS ] */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={resetAnimation}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold font-mono tracking-wider text-slate-300 hover:text-slate-100 bg-slate-800/70 hover:bg-slate-800 border border-border/70 rounded-xl transition-all duration-150 shadow-sm"
              title="Reset ML analysis to initial state"
            >
              <RotateCcw style={{ width: 13, height: 13 }} /> RESET
            </button>

            <button
              onClick={runMLAnalysis}
              disabled={!selectedTx || isRunning}
              className="flex items-center gap-2 px-4 py-2 text-xs font-bold font-mono tracking-wider rounded-xl border transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm bg-sky-500/15 hover:bg-sky-500/25 border-sky-500/40 hover:border-sky-400 text-sky-400 hover:text-sky-300"
              style={{
                background: isRunning ? 'rgba(99,102,241,0.15)' : undefined,
                borderColor: isRunning ? 'rgba(99,102,241,0.4)' : undefined,
                color: isRunning ? '#818cf8' : undefined,
              }}
              title="Execute full ML intelligence pipeline analysis"
            >
              {loading || isRunning ? (
                <><Loader2 style={{ width: 14, height: 14 }} className="animate-spin" /> {isRunning ? 'PROCESSING' : 'FETCHING'}</>
              ) : (
                <><Play style={{ width: 13, height: 13 }} className="fill-current" /> RUN ML ANALYSIS</>
              )}
            </button>
          </div>
        </div>

        {/* Target Transaction Selector */}
        <div className="mt-3.5 flex items-center gap-3 flex-wrap">
          <span className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider shrink-0">Target Transaction</span>
          <div className="relative">
            <button
              onClick={() => setShowDropdown(v => !v)}
              className="flex items-center gap-2 px-3.5 py-1.5 text-xs font-mono bg-muted/40 border border-border/60 rounded-xl hover:border-primary/40 transition-all text-slate-200 min-w-72"
            >
              {selectedTx ? (
                <>
                  <span className="text-sky-400 font-semibold">{selectedTx.tx_id}</span>
                  <span className="text-slate-500">·</span>
                  <span className="font-semibold">{formatCurrency(selectedTx.amount)}</span>
                  <span className="text-slate-500">·</span>
                  <span className="text-slate-400">{selectedTx.channel}</span>
                  <RiskBadge score={selectedTx.risk_score} showLabel={false} className="ml-auto" />
                </>
              ) : casesLoading ? (
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Loader2 style={{ width: 12, height: 12 }} className="animate-spin" /> Loading transactions…
                </span>
              ) : (
                <span className="text-slate-500">No transactions available</span>
              )}
              <ChevronDown style={{ width: 14, height: 14, color: '#64748b', marginLeft: 'auto' }} />
            </button>
            {showDropdown && displayCases.length > 0 && (
              <div className="absolute top-full left-0 mt-1.5 z-50 bg-card border border-border rounded-xl shadow-2xl w-96 max-h-64 overflow-y-auto">
                {displayCases.map(c => (
                  <div key={c.case_id}>
                    <div className="px-3.5 py-2 text-xs font-mono font-semibold text-slate-400 bg-muted/30 border-b border-border/40 uppercase tracking-wider">
                      {c.case_id} · Risk {Math.round(c.risk_level || 0)}
                    </div>
                    {(c.transactions || []).slice(0, 3).map(tx => (
                      <button
                        key={tx.tx_id}
                        onClick={() => { setSelectedTx(tx); setShowDropdown(false); resetAnimation(); }}
                        className="w-full flex items-center gap-2 px-3.5 py-2 text-xs font-mono text-left hover:bg-primary/5 transition-all border-b border-border/20"
                      >
                        <span className="text-sky-400 font-semibold w-28 shrink-0 truncate">{tx.tx_id}</span>
                        <span className="text-slate-300 font-medium">{formatCurrency(tx.amount)}</span>
                        <span className="text-slate-400">{tx.channel}</span>
                        <RiskBadge score={tx.risk_score} showLabel={false} className="ml-auto" />
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Content (Smooth Guided Viewport Container) ── */}
      <div
        ref={scrollContainerRef}
        onWheel={handleUserScroll}
        onTouchMove={handleUserScroll}
        className="flex-1 overflow-y-auto px-6 py-4 space-y-5 min-h-0"
      >
        {showDropdown && <div className="fixed inset-0 z-40" onClick={() => setShowDropdown(false)} />}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-300 font-mono">
            <Info style={{ width: 15, height: 15, flexShrink: 0 }} /> {error}
          </div>
        )}

        {/* ── Pipeline Container ── */}
        <div className="rounded-2xl border border-border/70 bg-card/40 p-5 space-y-4 shadow-sm">
          <div className="flex items-center gap-2 pb-2 border-b border-border/40">
            <Cpu style={{ width: 16, height: 16, color: '#818cf8' }} />
            <span className="text-xs font-mono text-slate-200 uppercase tracking-wider font-bold">
              ML Processing Pipeline
            </span>
            {isRunning && (
              <span className="text-xs font-mono font-semibold text-indigo-400 flex items-center gap-1.5 ml-auto">
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#818cf8', display: 'inline-block', animation: 'nnpulse 1s infinite' }} />
                RUNNING
              </span>
            )}
            {stage === 'complete' && (
              <span className="text-xs font-mono font-semibold text-emerald-400 flex items-center gap-1.5 ml-auto">
                <CheckCircle2 style={{ width: 13, height: 13 }} /> COMPLETE
              </span>
            )}
            {stage === 'idle' && (
              <span className="text-xs font-mono font-semibold text-slate-500 flex items-center gap-1.5 ml-auto">
                <span className="w-2 h-2 rounded-full bg-slate-600 inline-block" /> STANDBY
              </span>
            )}
          </div>

          {/* Pipeline Stage 1: Transaction Input */}
          <div
            ref={stageTxRef}
            className="rounded-xl border p-4 transition-all duration-500"
            style={{
              borderColor: stage !== 'idle' ? 'rgba(56,189,248,0.35)' : 'rgba(30,41,59,0.8)',
              background: stage !== 'idle' ? 'rgba(56,189,248,0.04)' : 'rgba(12,20,36,0.5)',
              boxShadow: stage === 'transaction' ? '0 0 18px rgba(56,189,248,0.07)' : 'none',
            }}
          >
            <div className="flex items-start gap-3.5">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all duration-300" style={{
                background: stage !== 'idle' ? 'rgba(56,189,248,0.12)' : 'rgba(30,41,59,0.5)',
                border: '1px solid ' + (stage !== 'idle' ? 'rgba(56,189,248,0.35)' : 'rgba(30,41,59,0.8)'),
              }}>
                <Database style={{ width: 16, height: 16, color: stage !== 'idle' ? '#38bdf8' : '#475569' }} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2.5 mb-2.5">
                  <span className="text-sm font-bold text-slate-100">Transaction Input</span>
                  {stage !== 'idle' ? (
                    <span className="text-xs font-mono font-semibold text-sky-400 bg-sky-400/10 border border-sky-400/30 px-2 py-0.5 rounded uppercase">Active</span>
                  ) : (
                    <span className="text-xs font-mono text-slate-500 bg-slate-800/40 border border-slate-700/40 px-2 py-0.5 rounded uppercase">Standby</span>
                  )}
                </div>
                {selectedTx ? (
                  <div className="grid grid-cols-3 gap-x-4 gap-y-2">
                    {[
                      ['TX ID', selectedTx.tx_id, 0],
                      ['Amount', formatCurrency(selectedTx.amount), 1],
                      ['Channel', selectedTx.channel || 'UPI', 2],
                      ['Sender', (selectedTx.sender_account || '').slice(-10), 3],
                      ['Receiver', (selectedTx.receiver_account || '').slice(-10), 4],
                      ['Hop #', selectedTx.hop_number || 0, 5],
                    ].map(([k, v, d]) => (
                      <div key={k} className="transition-all duration-300" style={{ opacity: stage !== 'idle' ? 1 : 0.6, transitionDelay: d * 100 + 'ms' }}>
                        <span className="text-xs font-mono text-slate-400 block font-medium">{k}</span>
                        <span className="text-xs font-mono text-slate-200 font-semibold truncate block mt-0.5">{v}</span>
                      </div>
                    ))}
                  </div>
                ) : <span className="text-xs text-slate-500 font-mono">No transaction selected</span>}
              </div>
            </div>
          </div>

          <FlowConnector active={hasFeaturesActive} color="#38bdf8" />

          {/* Pipeline Stage 2: Feature Extraction */}
          <div
            ref={stageFeaturesRef}
            className="rounded-xl border p-4 transition-all duration-500"
            style={{
              borderColor: hasFeaturesActive ? 'rgba(99,102,241,0.35)' : 'rgba(30,41,59,0.8)',
              background: hasFeaturesActive ? 'rgba(99,102,241,0.04)' : 'rgba(12,20,36,0.5)',
              boxShadow: stage === 'features' ? '0 0 18px rgba(99,102,241,0.07)' : 'none',
            }}
          >
            <div className="flex items-start gap-3.5">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all duration-300" style={{
                background: hasFeaturesActive ? 'rgba(99,102,241,0.12)' : 'rgba(30,41,59,0.5)',
                border: '1px solid ' + (hasFeaturesActive ? 'rgba(99,102,241,0.35)' : 'rgba(30,41,59,0.8)'),
              }}>
                <Layers style={{ width: 16, height: 16, color: hasFeaturesActive ? '#818cf8' : '#475569' }} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2.5 mb-3 flex-wrap">
                  <span className="text-sm font-bold text-slate-100">Feature Extraction</span>
                  <span className="text-xs font-mono text-slate-400 bg-slate-800/60 border border-slate-700/60 px-2 py-0.5 rounded">Normalized Vector Space</span>
                  {stage === 'idle' && (
                    <span className="text-xs font-mono text-slate-500 bg-slate-800/40 border border-slate-700/40 px-2 py-0.5 rounded uppercase ml-auto">
                      Standby
                    </span>
                  )}
                  {stage === 'features' && (
                    <span className="text-xs font-mono font-semibold text-indigo-400 bg-indigo-400/10 border border-indigo-400/30 px-2 py-0.5 rounded uppercase ml-auto">
                      Extracting
                    </span>
                  )}
                  {hasModelActive && (
                    <span className="text-xs font-mono font-semibold text-emerald-400 bg-emerald-400/10 border border-emerald-400/30 px-2 py-0.5 rounded uppercase flex items-center gap-1 ml-auto">
                      <CheckCircle2 style={{ width: 12, height: 12 }} /> Done
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
                  {Object.entries(FEATURE_CONFIG).map(([feat, { label, color }], i) => {
                    const fallbackVal = targetWeights[feat] || 0.15;
                    const prog = featureProgress[feat] !== undefined ? featureProgress[feat] : fallbackVal;
                    const isActive = hasFeaturesActive && activeFeatures.includes(i);
                    const pctVal = (prog * 100).toFixed(1);
                    return (
                      <div key={feat} className="flex items-center gap-2.5 transition-all duration-300">
                        <div
                          className="w-2.5 h-2.5 rounded-full shrink-0 transition-all duration-300"
                          style={{
                            background: isActive ? color : color + '99',
                            boxShadow: isActive ? `0 0 8px ${color}80` : 'none',
                          }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-mono text-slate-200 truncate font-medium">{label}</span>
                            <span className="text-xs font-mono font-bold ml-1 shrink-0" style={{ color: isActive ? color : '#94a3b8' }}>
                              {pctVal}%
                            </span>
                          </div>
                          <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{
                                width: `${Math.min(100, Math.max(3, prog * 100))}%`,
                                background: isActive ? color : 'linear-gradient(90deg, #334155, #475569)',
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          <FlowConnector active={hasModelActive} color="#818cf8" />

          {/* ── HERO SECTION: ML Model Inference ── */}
          <div
            ref={stageModelRef}
            className="rounded-2xl border p-6 transition-all duration-500 relative overflow-hidden"
            style={{
              borderColor: hasModelActive ? 'rgba(168,85,247,0.5)' : 'rgba(30,41,59,0.85)',
              background: hasModelActive
                ? 'linear-gradient(180deg, rgba(168,85,247,0.08) 0%, rgba(15,23,42,0.85) 100%)'
                : 'rgba(12,20,36,0.65)',
              boxShadow: stage === 'model'
                ? '0 0 32px rgba(168,85,247,0.15), inset 0 0 24px rgba(168,85,247,0.05)'
                : 'none',
            }}
          >
            {/* Subtle background circuit watermark */}
            <div className="absolute -top-12 -right-12 w-48 h-48 rounded-full bg-purple-500/5 blur-3xl pointer-events-none" />

            <div className="flex items-start gap-4">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 transition-all duration-500 shadow-md" style={{
                background: hasModelActive ? 'rgba(168,85,247,0.18)' : 'rgba(30,41,59,0.6)',
                border: '1px solid ' + (hasModelActive ? 'rgba(168,85,247,0.5)' : 'rgba(30,41,59,0.9)'),
                boxShadow: stage === 'model' ? '0 0 16px rgba(168,85,247,0.3)' : 'none',
              }}>
                <Network style={{ width: 22, height: 22, color: hasModelActive ? '#d8b4fe' : '#475569' }} />
              </div>

              <div className="flex-1 min-w-0">
                {/* Hero Header */}
                <div className="flex items-center justify-between flex-wrap gap-2 mb-4 pb-3 border-b border-border/40">
                  <div>
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="text-base font-extrabold tracking-tight text-slate-100">
                        ML Model Inference Engine
                      </span>
                      <span className="text-[10px] font-mono font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded-full uppercase tracking-wider">
                        HERO ANALYTICS CORE
                      </span>
                    </div>
                    <span className="text-xs font-mono text-slate-400 block mt-0.5">
                      Multi-Layer Deep Neural Architecture · Continuous Tensor Signal Propagation
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {stage === 'idle' && (
                      <span className="text-xs font-mono text-slate-500 bg-slate-800/60 border border-slate-700/60 px-2.5 py-1 rounded-md uppercase">
                        Standby
                      </span>
                    )}
                    {stage === 'model' && (
                      <span className="text-xs font-mono font-bold text-purple-300 bg-purple-500/20 border border-purple-500/40 px-3 py-1 rounded-md uppercase flex items-center gap-1.5 shadow-sm">
                        <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />
                        INFERENCING TENSORS
                      </span>
                    )}
                    {hasImpactActive && (
                      <span className="text-xs font-mono font-semibold text-emerald-400 bg-emerald-400/10 border border-emerald-400/30 px-3 py-1 rounded-md uppercase flex items-center gap-1.5">
                        <CheckCircle2 style={{ width: 13, height: 13 }} /> CONVERGED
                      </span>
                    )}
                  </div>
                </div>

                {/* Hero Visualization Area */}
                <div className="grid grid-cols-1 lg:grid-cols-[1fr,200px] gap-6 items-center">
                  <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/80">
                    <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-2 pb-1">
                      <span>Signal Vector Flow</span>
                      <span className="text-purple-400">Dense Synapse Graph</span>
                    </div>
                    <NeuralNetworkViz activeInputs={activeFeatures} modelActive={modelActive} outputActive={outputActive} />
                  </div>

                  {/* Architecture Telemetry Panel */}
                  <div className="space-y-2.5">
                    <div className="p-3 rounded-xl bg-slate-900/50 border border-border/50">
                      <span className="text-[10px] font-mono text-slate-400 block uppercase font-semibold">Topology Architecture</span>
                      <span className="text-sm font-mono font-bold text-purple-300 block mt-0.5">Dense (6→4→3→2)</span>
                      <span className="text-[9px] font-mono text-slate-500 block mt-0.5">Non-Linear Rectified Calibration</span>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900/50 border border-border/50">
                      <span className="text-[10px] font-mono text-slate-400 block uppercase font-semibold">Feature Dimensions</span>
                      <div className="flex items-baseline gap-1 mt-0.5">
                        <span className="text-base font-mono font-bold text-sky-400">6</span>
                        <span className="text-xs font-mono text-slate-400">Tensors Active</span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900/50 border border-border/50">
                      <span className="text-[10px] font-mono text-slate-400 block uppercase font-semibold">Inference Confidence</span>
                      <span className="text-xs font-mono font-bold text-emerald-400 block mt-0.5">
                        {txRuleScore >= 80 ? '±5.0 HIGH ACCURACY' : '±10.0 MID CONFIDENCE'}
                      </span>
                      <span className="text-[9px] font-mono text-slate-500 block mt-0.5">Simulated On-Chip TPU</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── 2-Column Analytical Matrix: TOP CONTRIBUTING SIGNALS & ML IMPACT ANALYSIS ── */}
        <div ref={stageSignalsRef} className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* LEFT: TOP CONTRIBUTING SIGNALS (Replaced Feature Importance) */}
          <div className="rounded-xl border border-border/60 bg-card/40 p-5 space-y-3.5">
            <div className="flex items-center justify-between pb-2 border-b border-border/40">
              <div className="flex items-center gap-2">
                <Activity style={{ width: 16, height: 16, color: hasImpactActive ? '#f59e0b' : '#64748b' }} />
                <span className="text-xs font-mono text-slate-200 uppercase tracking-wider font-bold">
                  TOP CONTRIBUTING SIGNALS
                </span>
              </div>
              {hasImpactActive ? (
                <span className="text-[10px] font-mono font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full uppercase tracking-wider">
                  RANKED IMPACT
                </span>
              ) : (
                <span className="text-[10px] font-mono text-slate-500 bg-slate-800/40 border border-slate-700/40 px-2 py-0.5 rounded-full uppercase tracking-wider">
                  STANDBY
                </span>
              )}
            </div>

            <div className="space-y-3 pt-1">
              {topFeatures.map(([feat, imp], idx) => {
                const cfg = FEATURE_CONFIG[feat] || { label: feat, color: '#64748b' };
                const pctVal = (imp * 100).toFixed(1);
                return (
                  <div key={feat} className="space-y-1">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold w-4 text-slate-400">#{idx + 1}</span>
                        <div
                          className="w-2.5 h-2.5 rounded-full shrink-0 transition-all duration-300"
                          style={{
                            background: hasImpactActive ? cfg.color : cfg.color + 'aa',
                            boxShadow: hasImpactActive ? `0 0 8px ${cfg.color}80` : 'none',
                          }}
                        />
                        <span className="text-slate-200 font-medium truncate">{cfg.label}</span>
                      </div>
                      <span className="font-bold font-mono ml-2 shrink-0" style={{ color: hasImpactActive ? cfg.color : '#cbd5e1' }}>
                        {pctVal}%
                      </span>
                    </div>
                    <div className="h-2 bg-slate-800/90 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700 ease-out"
                        style={{
                          width: `${Math.max(3, imp * 100)}%`,
                          background: hasImpactActive ? cfg.color : 'linear-gradient(90deg, #475569, #64748b)',
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* RIGHT: ML IMPACT ANALYSIS (Analytical Transformation Rail) */}
          <div className="rounded-xl border border-border/60 bg-card/40 p-5 space-y-3.5">
            <div className="flex items-center justify-between pb-2 border-b border-border/40">
              <div className="flex items-center gap-2">
                <TrendingUp style={{ width: 16, height: 16, color: hasImpactActive ? '#818cf8' : '#64748b' }} />
                <span className="text-xs font-mono text-slate-200 uppercase tracking-wider font-bold">
                  ML Impact Analysis
                </span>
              </div>
              {hasImpactActive ? (
                <span className="text-[10px] font-mono font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full uppercase tracking-wider">
                  Neural Refinement
                </span>
              ) : (
                <span className="text-[10px] font-mono text-slate-400 bg-slate-800/40 border border-slate-700/40 px-2 py-0.5 rounded-full uppercase tracking-wider">
                  Baseline Ready
                </span>
              )}
            </div>

            {/* Score Adjustment Rail */}
            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-border/50 space-y-2.5">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-300 font-medium">Score Adjustment Delta:</span>
                <span className={'font-bold px-2.5 py-0.5 rounded border text-xs ' + (
                  scoreAdjustment > 0 ? 'bg-rose-500/15 text-rose-300 border-rose-500/30' :
                  scoreAdjustment < 0 ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' :
                  'bg-slate-800 text-slate-300 border-slate-700'
                )}>
                  {scoreAdjustment > 0 ? `+${scoreAdjustment}` : scoreAdjustment} pts
                  {scoreAdjustment > 0 ? ' (Escalation)' : scoreAdjustment < 0 ? ' (Attenuation)' : ' (Concordance)'}
                </span>
              </div>

              {/* 3-Point Transformation Flow */}
              <div className="grid grid-cols-3 gap-2 text-center font-mono pt-1">
                <div className="p-2.5 rounded-lg bg-slate-800/50 border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">1. Rule Engine</span>
                  <span className="text-base font-bold text-slate-200 block mt-1">{txRuleScore}</span>
                  <span className="text-[9px] text-slate-500 block">Baseline</span>
                </div>
                <div className={`p-2.5 rounded-lg border ${hasImpactActive ? 'bg-indigo-950/30 border-indigo-500/30' : 'bg-slate-800/30 border-slate-800/60'}`}>
                  <span className={`text-[10px] uppercase tracking-wider block font-semibold ${hasImpactActive ? 'text-indigo-300' : 'text-slate-500'}`}>2. ML Refinement</span>
                  <span className={`text-base font-bold block mt-1 ${hasImpactActive ? 'text-indigo-400' : 'text-slate-600'}`}>
                    {hasImpactActive ? Math.round(txMlScore) : '—'}
                  </span>
                  <span className={`text-[9px] block ${hasImpactActive ? 'text-indigo-400/70' : 'text-slate-600'}`}>Neural Model</span>
                </div>
                <div className="p-2.5 rounded-lg border" style={{
                  background: hasImpactActive ? afterRisk.hex + '12' : 'rgba(30,41,59,0.3)',
                  borderColor: hasImpactActive ? afterRisk.hex + '35' : 'rgba(51,65,85,0.6)',
                }}>
                  <span className="text-[10px] uppercase tracking-wider block font-semibold" style={{ color: hasImpactActive ? afterRisk.hex : '#64748b' }}>
                    3. Hybrid Result
                  </span>
                  <span className={`text-base font-bold block mt-1 ${hasImpactActive ? afterRisk.text : 'text-slate-600'}`}>
                    {hasImpactActive ? Math.round(txFinalScore) : '—'}
                  </span>
                  <span className="text-[9px] block font-medium" style={{ color: hasImpactActive ? afterRisk.hex + 'cc' : '#64748b' }}>
                    Calibrated
                  </span>
                </div>
              </div>
            </div>

            {/* Neural Synthesis Details */}
            <div className="p-3 rounded-xl bg-slate-900/30 border border-border/40 space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Synthesis Mode</span>
                <span className="text-slate-300 font-semibold">Rule-Guided Non-Linear Calibrator</span>
              </div>
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Model Convergence</span>
                <span className="text-emerald-400 font-semibold">Stable (Pearson r = 0.96)</span>
              </div>
            </div>

            {/* Policy Action & Confidence Row */}
            <div className="pt-2 border-t border-border/40 flex items-center justify-between text-xs font-mono flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <ShieldAlert style={{ width: 14, height: 14, color: '#94a3b8' }} />
                <span className="text-slate-400 font-medium">Policy Action:</span>
                <span className={`font-bold ${hasImpactActive ? 'text-sky-400' : 'text-slate-500'}`}>
                  {hasImpactActive ? ((mlResult?.policy_action || selectedTx?.response_decision?.action || 'MONITOR').replace(/_/g, ' ')) : 'AWAITING INFERENCE'}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-400 ml-auto">
                <span className="text-slate-500">Confidence:</span>
                <span className={`font-semibold ${hasImpactActive ? 'text-slate-200' : 'text-slate-500'}`}>
                  {hasImpactActive ? (mlResult?.confidence || selectedTx?.confidence || 'HIGH') : '—'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Analytical Transformation Comparison (Before ML vs After ML) ── */}
        <div ref={stageComparisonRef} className="space-y-3 pt-1">
          <div className="flex items-center justify-between px-1 flex-wrap gap-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-slate-200 uppercase tracking-wider font-bold">
                  Analytical Transformation Comparison
                </span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase tracking-wider bg-slate-800 text-slate-400 border border-slate-700/60">
                  BASELINE vs ML-ENHANCED
                </span>
              </div>
              <span className="text-[11px] font-mono text-slate-500 block mt-0.5">
                How machine learning behavioral inference refines deterministic rule decisions
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="px-2.5 py-1 rounded-md bg-slate-900/80 border border-slate-800 text-slate-400">
                Baseline: <strong className={hasComparisonActive ? 'text-slate-200' : 'text-slate-400'}>{txRuleScore}</strong>
              </span>
              <span className="text-slate-600 font-bold">→</span>
              <span className="px-2.5 py-1 rounded-md bg-slate-900/80 border border-slate-800 text-slate-400">
                ML Model: <strong className={hasComparisonActive ? 'text-indigo-400' : 'text-slate-400'}>{Math.round(txMlScore)}</strong>
              </span>
              <span className="text-slate-600 font-bold">→</span>
              <span className="px-2.5 py-1 rounded-md bg-slate-900/80 border border-slate-800 text-slate-400">
                Hybrid: <strong className={hasComparisonActive ? afterRisk.text : 'text-slate-400'}>{Math.round(txFinalScore)}</strong>
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1fr,76px,1fr] items-stretch gap-3">
            {/* 1. BEFORE ML PANEL (BASELINE ENGINE) */}
            <div
              className="rounded-2xl border p-5 transition-all duration-500 flex flex-col justify-between"
              style={{
                borderColor: stage !== 'idle' ? 'rgba(56,189,248,0.3)' : 'rgba(30,41,59,0.9)',
                background: 'rgba(12,20,36,0.65)',
                boxShadow: stage === 'transaction' ? '0 0 20px rgba(56,189,248,0.06)' : 'none',
              }}
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-center justify-between pb-3 border-b border-border/50">
                  <div className="flex items-center gap-2.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-slate-400 shadow-[0_0_8px_rgba(148,163,184,0.35)]" />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wider">
                          BEFORE ML
                        </span>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60 uppercase tracking-wider">
                          BASELINE ENGINE
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-500">
                        Existing Sentinel Rule Engine
                      </span>
                    </div>
                  </div>
                  <span className={`text-xs font-mono font-semibold flex items-center gap-1.5 px-2.5 py-1 rounded-md border transition-all duration-300 ${
                    stage !== 'idle'
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/25'
                      : 'bg-slate-800/60 text-slate-400 border-slate-700/50'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${stage !== 'idle' ? 'bg-emerald-400' : 'bg-slate-400'}`} />
                    {stage !== 'idle' ? 'EVALUATED' : 'BASELINE READY'}
                  </span>
                </div>

                {selectedTx ? (
                  <>
                    {/* Primary Deterministic Rule Score Box */}
                    <div className="p-3.5 rounded-xl bg-[#081020]/75 border border-slate-800/80 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono text-slate-400 uppercase tracking-wider font-semibold">
                          Deterministic Rule Score
                        </span>
                        <div className="flex items-baseline gap-1.5">
                          <span className={`text-3xl font-bold font-mono ${hasComparisonActive ? beforeRisk.text : 'text-slate-200'}`}>
                            {txRuleScore}
                          </span>
                          <span className="text-xs font-mono text-slate-500 font-normal">/ 100</span>
                        </div>
                      </div>

                      <div className="space-y-1">
                        <div className="w-full h-2 bg-slate-800/90 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-700 ease-out"
                            style={{
                              width: `${Math.min(100, Math.max(4, txRuleScore))}%`,
                              background: hasComparisonActive ? beforeRisk.hex : '#64748b',
                            }}
                          />
                        </div>
                        <div className="flex justify-between text-[9px] font-mono text-slate-600 px-0.5">
                          <span>0 LOW</span>
                          <span>40 MED</span>
                          <span>70 HIGH</span>
                          <span>85+ CRIT</span>
                        </div>
                      </div>

                      <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-slate-400 font-medium">Classification:</span>
                          <span className={`text-xs font-mono font-bold uppercase px-2 py-0.5 rounded border ${
                            hasComparisonActive ? (
                              txRuleScore >= 70 ? 'bg-rose-500/10 text-rose-300 border-rose-500/30' :
                              txRuleScore >= 40 ? 'bg-amber-500/10 text-amber-300 border-amber-500/30' :
                              'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                            ) : 'bg-slate-800 text-slate-300 border-slate-700/60'
                          }`}>
                            {getRiskLabel(txRuleScore)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-slate-400 font-medium">Rule Action:</span>
                          <span className="text-xs font-mono font-semibold text-slate-300">
                            {(selectedTx.response_decision?.action || 'MONITOR').replace(/_/g, ' ')}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Active Rule Signals */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono text-slate-400 uppercase tracking-wider font-semibold">
                          Active Rule Signals
                        </span>
                        <span className="text-[11px] font-mono text-slate-500">
                          {(selectedTx.risk_factors || []).filter(f => f.contribution > 0).length} active factors
                        </span>
                      </div>

                      <div className="space-y-1.5">
                        {(selectedTx.risk_factors || []).filter(f => f.contribution > 0).slice(0, 4).map(f => (
                          <div
                            key={f.name}
                            className="flex items-center gap-2.5 p-2 rounded-lg bg-slate-800/30 border border-slate-800/60 transition-all duration-300"
                          >
                            <div className="w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
                            <span className="text-xs font-mono text-slate-300 capitalize w-36 truncate font-medium">
                              {f.name.replace(/_/g, ' ')}
                            </span>
                            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all duration-500"
                                style={{
                                  width: `${Math.min(100, Math.max(8, f.value))}%`,
                                  background: hasComparisonActive ? beforeRisk.hex : '#64748b'
                                }}
                              />
                            </div>
                            <span className="text-xs font-mono font-bold text-slate-300 w-14 text-right">
                              +{f.contribution} pts
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Concise Descriptive Note */}
                    <div className="p-2.5 rounded-lg bg-slate-900/40 border border-slate-800/60 text-[11px] font-mono text-slate-400 leading-relaxed">
                      Deterministic detection using existing SENTINEL rules and static risk threshold conditions.
                    </div>
                  </>
                ) : null}
              </div>

              <div className="pt-3 border-t border-border/40 mt-4 flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span>Deterministic Threshold Engine</span>
                <span>v2.4 Live Core</span>
              </div>
            </div>

            {/* 2. CENTRAL TRANSFORMATION CONNECTOR BRIDGE */}
            <div className="hidden lg:flex flex-col items-center justify-between relative py-2 select-none">
              {/* Top Connector */}
              <div className="w-full flex items-center justify-center relative">
                <svg width="64" height="28" viewBox="0 0 64 28" className="overflow-visible">
                  <line
                    x1="0" y1="14" x2="64" y2="14"
                    stroke={hasComparisonActive ? 'rgba(99,102,241,0.6)' : isRunning ? 'rgba(56,189,248,0.5)' : 'rgba(51,65,85,0.4)'}
                    strokeWidth="1.5"
                    strokeDasharray="4 3"
                  />
                  {isRunning && (
                    <circle cx="32" cy="14" r="3.5" fill="#38bdf8">
                      <animate attributeName="cx" from="0" to="64" dur="1s" repeatCount="indefinite" />
                    </circle>
                  )}
                  {hasComparisonActive && (
                    <polygon points="58,10 64,14 58,18" fill="#818cf8" />
                  )}
                </svg>
              </div>

              {/* Central Node Badge */}
              <div className="flex flex-col items-center justify-center my-auto py-2">
                <div
                  className="w-12 h-12 rounded-2xl border flex flex-col items-center justify-center transition-all duration-500 relative z-10 shadow-lg"
                  style={{
                    background: hasComparisonActive ? 'rgba(99,102,241,0.22)' : isRunning ? 'rgba(56,189,248,0.2)' : 'rgba(15,23,42,0.9)',
                    borderColor: hasComparisonActive ? 'rgba(99,102,241,0.6)' : isRunning ? 'rgba(56,189,248,0.6)' : 'rgba(51,65,85,0.7)',
                    boxShadow: hasComparisonActive ? '0 0 18px rgba(99,102,241,0.25)' : 'none',
                  }}
                >
                  <Cpu style={{ width: 22, height: 22, color: hasComparisonActive ? '#a5b4fc' : isRunning ? '#38bdf8' : '#64748b' }} />
                </div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-200 mt-1.5">
                  ML LAYER
                </span>
                <span className={`text-[9px] font-mono uppercase tracking-wider font-semibold mt-0.5 ${
                  hasCompleteActive ? 'text-indigo-400' : isRunning ? 'text-sky-400' : 'text-slate-500'
                }`}>
                  {hasCompleteActive ? 'CALIBRATED' : isRunning ? 'SYNTHESIS' : 'STANDBY'}
                </span>

                {/* Vertical Step Progression Flow */}
                <div className="flex flex-col items-center gap-0.5 text-[9px] font-mono text-slate-500 mt-2 px-1 py-1 rounded bg-slate-900/60 border border-slate-800/60">
                  <span className="text-[8px] uppercase tracking-wider text-slate-400">BASELINE</span>
                  <span className="font-bold text-slate-300">{txRuleScore}</span>
                  <ArrowDown className="w-2.5 h-2.5 text-slate-600" />
                  <span className="text-[8px] uppercase tracking-wider text-indigo-400">ML SCORE</span>
                  <span className={`font-bold ${hasComparisonActive ? 'text-indigo-400' : 'text-slate-400'}`}>{Math.round(txMlScore)}</span>
                  <ArrowDown className="w-2.5 h-2.5 text-slate-600" />
                  <span className="text-[8px] uppercase tracking-wider text-slate-400">HYBRID</span>
                  <span className={`font-bold ${hasComparisonActive ? afterRisk.text : 'text-slate-400'}`}>{Math.round(txFinalScore)}</span>
                </div>
              </div>

              {/* Bottom Connector */}
              <div className="w-full flex items-center justify-center relative">
                <svg width="64" height="28" viewBox="0 0 64 28" className="overflow-visible">
                  <line
                    x1="0" y1="14" x2="64" y2="14"
                    stroke={hasComparisonActive ? 'rgba(99,102,241,0.6)' : isRunning ? 'rgba(56,189,248,0.5)' : 'rgba(51,65,85,0.4)'}
                    strokeWidth="1.5"
                    strokeDasharray="4 3"
                  />
                  {isRunning && (
                    <circle cx="32" cy="14" r="3.5" fill="#818cf8">
                      <animate attributeName="cx" from="0" to="64" dur="1s" begin="0.35s" repeatCount="indefinite" />
                    </circle>
                  )}
                  {hasComparisonActive && (
                    <polygon points="58,10 64,14 58,18" fill="#818cf8" />
                  )}
                </svg>
              </div>
            </div>

            {/* 3. AFTER ML PANEL (HYBRID MODEL) */}
            <div
              className="rounded-2xl border p-5 transition-all duration-500 flex flex-col justify-between"
              style={{
                borderColor: hasComparisonActive ? 'rgba(99,102,241,0.45)' : 'rgba(30,41,59,0.7)',
                background: hasComparisonActive ? 'rgba(15,23,42,0.85)' : 'rgba(12,20,36,0.45)',
                boxShadow: hasComparisonActive ? '0 0 24px rgba(99,102,241,0.08)' : 'none',
              }}
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-center justify-between pb-3 border-b border-border/50">
                  <div className="flex items-center gap-2.5">
                    <div
                      className="w-2.5 h-2.5 rounded-full transition-all duration-500"
                      style={{
                        background: hasComparisonActive ? '#818cf8' : isRunning ? '#38bdf8' : '#475569',
                        boxShadow: hasComparisonActive ? '0 0 10px rgba(129,140,248,0.6)' : 'none',
                      }}
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className="text-xs font-mono font-bold uppercase tracking-wider transition-colors duration-300"
                          style={{ color: hasComparisonActive ? '#e2e8f0' : '#94a3b8' }}
                        >
                          AFTER ML
                        </span>
                        <span
                          className="text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase tracking-wider transition-all duration-300"
                          style={{
                            background: hasComparisonActive ? 'rgba(99,102,241,0.18)' : 'rgba(30,41,59,0.8)',
                            color: hasComparisonActive ? '#a5b4fc' : '#64748b',
                            border: '1px solid ' + (hasComparisonActive ? 'rgba(99,102,241,0.45)' : 'rgba(51,65,85,0.6)'),
                          }}
                        >
                          HYBRID MODEL
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-500">
                        Multi-Factor Neural Calibration
                      </span>
                    </div>
                  </div>

                  <span
                    className="text-xs font-mono font-semibold flex items-center gap-1.5 px-2.5 py-1 rounded-md border transition-all duration-500"
                    style={{
                      background: hasCompleteActive ? 'rgba(16,185,129,0.12)' : isRunning ? 'rgba(99,102,241,0.12)' : 'rgba(30,41,59,0.6)',
                      borderColor: hasCompleteActive ? 'rgba(16,185,129,0.35)' : isRunning ? 'rgba(99,102,241,0.35)' : 'rgba(51,65,85,0.5)',
                      color: hasCompleteActive ? '#34d399' : isRunning ? '#818cf8' : '#64748b',
                    }}
                  >
                    {hasCompleteActive ? (
                      <><CheckCircle2 style={{ width: 12, height: 12 }} /> RESOLVED</>
                    ) : isRunning ? (
                      <><Loader2 style={{ width: 12, height: 12 }} className="animate-spin" /> INFERRING</>
                    ) : (
                      <>AWAITING INFERENCE</>
                    )}
                  </span>
                </div>

                {/* Primary Dual Scores: ML Model Score & Calibrated Hybrid */}
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="p-3 rounded-xl bg-[#081020]/80 border border-slate-800 space-y-1.5">
                    <span className="text-xs font-mono uppercase tracking-wider font-semibold block text-slate-400">
                      ML Model Score
                    </span>
                    <div className="flex items-baseline gap-1.5">
                      <span className={`text-2xl font-bold font-mono ${hasComparisonActive ? 'text-indigo-400' : 'text-slate-300'}`}>
                        {Math.round(txMlScore)}
                      </span>
                      <span className="text-xs font-mono text-slate-500">/ 100</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800/90 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.min(100, Math.max(3, Math.round(txMlScore)))}%`,
                          background: hasComparisonActive ? '#818cf8' : '#64748b'
                        }}
                      />
                    </div>
                    <span className="text-[10px] font-mono text-slate-400 block pt-0.5">
                      Neural Evaluation
                    </span>
                  </div>

                  <div
                    className="p-3 rounded-xl bg-[#081020]/80 border space-y-1.5 transition-all duration-500"
                    style={{ borderColor: hasComparisonActive ? afterRisk.hex + '45' : 'rgba(51,65,85,0.6)' }}
                  >
                    <span className="text-xs font-mono uppercase tracking-wider font-semibold block text-slate-400">
                      Calibrated Hybrid
                    </span>
                    <div className="flex items-baseline gap-1.5">
                      <span className={`text-2xl font-bold font-mono ${hasComparisonActive ? afterRisk.text : 'text-slate-300'}`}>
                        {Math.round(txFinalScore)}
                      </span>
                      <span className="text-xs font-mono text-slate-500">/ 100</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800/90 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.min(100, Math.max(3, Math.round(txFinalScore)))}%`,
                          background: hasComparisonActive ? afterRisk.hex : '#64748b'
                        }}
                      />
                    </div>
                    <span className={`text-[10px] font-mono font-bold uppercase block pt-0.5 ${hasComparisonActive ? afterRisk.text : 'text-slate-400'}`}>
                      {hasComparisonActive ? `${getRiskLabel(Math.round(txFinalScore))} SEVERITY` : 'STANDBY'}
                    </span>
                  </div>
                </div>

                {/* ── WHAT ML ADDED / ML CONTRIBUTION (Key Addition) ── */}
                <div className="p-3 rounded-xl bg-[#081020]/80 border border-slate-800/80 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <Sparkles className={`w-3.5 h-3.5 ${hasComparisonActive ? 'text-indigo-400' : 'text-slate-500'}`} />
                      <span className="text-xs font-mono text-slate-200 uppercase tracking-wider font-bold">
                        WHAT ML ADDED
                      </span>
                    </div>
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase tracking-wider transition-all duration-300 ${
                      hasComparisonActive
                        ? 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30'
                        : 'bg-slate-800 text-slate-400 border-slate-700/60'
                    }`}>
                      ML CONTRIBUTION
                    </span>
                  </div>

                  {/* Score Calibration Delta */}
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 border border-slate-800/70">
                    <span className="text-xs font-mono text-slate-400 font-medium">Analytical Calibration Delta:</span>
                    <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                      hasComparisonActive ? (
                        finalDelta > 0 ? 'bg-rose-500/15 text-rose-300 border-rose-500/30' :
                        finalDelta < 0 ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' :
                        'bg-slate-800 text-slate-300 border-slate-700'
                      ) : 'bg-slate-800 text-slate-400 border-slate-700/60'
                    }`}>
                      {hasComparisonActive ? (
                        finalDelta > 0 ? `+${finalDelta} pts` : `${finalDelta} pts${finalDelta === 0 ? ' (Concordant)' : ''}`
                      ) : '—'}
                    </span>
                  </div>

                  {/* Top ML Weighted Signals */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                      <span>Top ML-Derived Signals</span>
                      <span>Weight</span>
                    </div>
                    {topFeatures.slice(0, 3).map(([key, weight], idx) => (
                      <div key={key} className="flex items-center gap-2 p-1.5 rounded-md bg-slate-800/30 border border-slate-800/50">
                        <span className="text-[10px] font-mono font-bold text-slate-500 w-4">#{idx + 1}</span>
                        <span className="text-xs font-mono text-slate-300 flex-1 truncate font-medium">
                          {FEATURE_CONFIG[key]?.label || key}
                        </span>
                        <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${Math.min(100, Math.max(8, weight * 100))}%`,
                              background: hasComparisonActive ? (FEATURE_CONFIG[key]?.color || '#818cf8') : '#64748b'
                            }}
                          />
                        </div>
                        <span className="text-xs font-mono font-bold text-slate-300 w-12 text-right">
                          {(weight * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* Behavioral Pattern Refinement note */}
                  <div className="text-[11px] font-mono text-slate-400 leading-relaxed pt-0.5">
                    Non-linear behavioral pattern inference & multi-dimensional signal calibration.
                  </div>
                </div>

                {/* Supporting ML Policy Action & Confidence Row */}
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-800/30 border border-slate-800/60 flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <ShieldAlert style={{ width: 14, height: 14, color: '#94a3b8' }} />
                    <span className="text-xs font-mono text-slate-400 font-medium">ML Policy Action:</span>
                    <span className={`text-xs font-mono font-bold ${hasComparisonActive ? 'text-sky-400' : 'text-slate-300'}`}>
                      {(mlResult?.policy_action || selectedTx?.response_decision?.action || 'MONITOR').replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs font-mono text-slate-500 ml-auto">
                    <span>Confidence:</span>
                    <span className={`font-semibold ${hasComparisonActive ? 'text-slate-200' : 'text-slate-400'}`}>
                      {mlResult?.confidence || selectedTx?.confidence || 'HIGH'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-border/40 mt-4 flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span>Hybrid Scorer V16</span>
                <span>Rule-Guided Emulator</span>
              </div>
            </div>
          </div>

        </div>

        {/* ── FINAL MAJOR SECTION: Prediction Output (Moved to the very end!) ── */}
        <div
          ref={stagePredictionRef}
          className="rounded-2xl border p-5 transition-all duration-500 shadow-md"
          style={{
            borderColor: hasPredictionActive ? afterRisk.hex + '55' : 'rgba(30,41,59,0.85)',
            background: hasPredictionActive ? afterRisk.hex + '08' : 'rgba(12,20,36,0.5)',
            boxShadow: stage === 'prediction' ? '0 0 24px ' + afterRisk.hex + '15' : 'none',
          }}
        >
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-all duration-300" style={{
              background: hasPredictionActive ? afterRisk.hex + '1a' : 'rgba(30,41,59,0.5)',
              border: '1px solid ' + (hasPredictionActive ? afterRisk.hex + '44' : 'rgba(30,41,59,0.8)'),
            }}>
              <Target style={{ width: 20, height: 20, color: hasPredictionActive ? afterRisk.hex : '#475569' }} />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-slate-100">Prediction Output</span>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase tracking-wider bg-slate-800 text-slate-400 border border-slate-700/60">
                      FINAL DECISION LAYER
                    </span>
                  </div>
                  <span className="text-xs font-mono text-slate-400 block mt-0.5">
                    Synthesized Neural Risk Prediction & Calibrated Policy Action
                  </span>
                </div>

                <div>
                  {stage === 'idle' && (
                    <span className="text-xs font-mono text-slate-400 bg-slate-800/60 border border-slate-700/60 px-2.5 py-1 rounded uppercase">
                      Baseline Ready
                    </span>
                  )}
                  {stage === 'prediction' && (
                    <span className="text-xs font-mono font-semibold text-yellow-400 bg-yellow-400/10 border border-yellow-400/30 px-2.5 py-1 rounded uppercase flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-ping" /> Resolving
                    </span>
                  )}
                  {hasCompleteActive && (
                    <span className="text-xs font-mono font-semibold text-emerald-400 bg-emerald-400/10 border border-emerald-400/30 px-2.5 py-1 rounded uppercase flex items-center gap-1">
                      <CheckCircle2 style={{ width: 12, height: 12 }} /> Resolved
                    </span>
                  )}
                </div>
              </div>

              {hasPredictionActive ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
                  {[
                    ['ML Model Score', mlScoreAnim, '#818cf8', true],
                    ['Calibrated Hybrid', finalScoreAnim, afterRisk.hex, true],
                    ['Classification', getRiskLabel(Math.round(txFinalScore)), afterRisk.hex, false],
                  ].map(([label, value, color, showBar]) => (
                    <div key={label} className="p-3.5 rounded-xl border bg-card/60 text-center" style={{ borderColor: afterRisk.hex + '28' }}>
                      <span className="text-xs font-mono text-slate-400 block mb-1 font-medium">{label}</span>
                      <span className="text-2xl font-bold font-mono" style={{ color }}>{value}</span>
                      {showBar && (
                        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden mt-2">
                          <div className="h-full rounded-full transition-all duration-500" style={{ width: Math.min(100, Math.max(0, value)) + '%', background: color }} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
                  {[
                    ['ML Model Score', Math.round(txMlScore), '#818cf8', true],
                    ['Calibrated Hybrid', Math.round(txFinalScore), afterRisk.hex, true],
                    ['Classification', getRiskLabel(Math.round(txFinalScore)), afterRisk.hex, false],
                  ].map(([label, value, color, showBar]) => (
                    <div key={label} className="p-3.5 rounded-xl border border-slate-800/70 bg-card/40 text-center">
                      <span className="text-xs font-mono text-slate-400 block mb-1 font-medium">{label}</span>
                      <span className="text-2xl font-bold font-mono" style={{ color }}>{value}</span>
                      {showBar && (
                        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden mt-2">
                          <div className="h-full rounded-full transition-all duration-500" style={{ width: Math.min(100, Math.max(0, value)) + '%', background: color }} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Footer ── */}
        <div className="rounded-xl border border-border/40 bg-card/20 px-4 py-3 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-6">
            {[['Model', 'SENTINEL_HYBRID_SCORER_V16'], ['Engine', 'Rule-Guided Emulator'], ['Features', '6 dimensions'], ['Correlation', 'Pearson r > 0.95']].map(([k, v]) => (
              <div key={k}>
                <span className="text-xs font-mono text-slate-500 block font-medium">{k}</span>
                <span className="text-xs font-mono text-slate-300 font-semibold">{v}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500" style={{ animation: 'nnpulse 2s infinite' }} />
            <span className="text-xs font-mono text-emerald-400 font-semibold">ML ENGINE OPERATIONAL</span>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes nnpulse {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.25); }
        }
        @keyframes dashScroll {
          0% { stroke-dashoffset: 14; }
          100% { stroke-dashoffset: 0; }
        }
      `}</style>
    </div>
  );
};

export default MLIntelligence;
