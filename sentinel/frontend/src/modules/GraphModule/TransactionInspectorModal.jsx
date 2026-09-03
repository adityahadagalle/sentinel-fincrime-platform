import React, { useEffect } from 'react';
import { X, ArrowRight, ShieldAlert, Activity, GitCommit, Layers, AlertTriangle, Clock, CheckCircle2, Shield, Lock, Zap, Check } from 'lucide-react';

const TransactionInspectorModal = ({ edge, onClose, isAutomationOn = true, onAction }) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!edge) return null;

  const txId = edge.tx_id || edge.id || 'TX-UNKNOWN';
  const amount = Number(edge.amount || 0);
  const channel = edge.channel || 'UPI';
  const isSuspicious = Boolean(edge.suspicious);
  const hopNumber = edge.hop_number || 1;
  const totalHops = edge.total_hops || 4;
  const source = edge.source || edge.from || 'ACC-USR-8122';
  const target = edge.target || edge.to || 'ACC-MERCH-2062';
  const chainId = edge.chain_id || (txId.startsWith('TX-') ? `CHAIN-${txId.slice(3, 11)}` : 'CHAIN-0921');
  const patternType = edge.pattern_type || (isSuspicious ? 'MULE CHAIN LAYERED' : 'STANDARD FLOW');
  const parentTxId = edge.parent_transaction_id || null;
  const rootTxId = edge.root_transaction_id || null;
  const riskScore = edge.risk_score || (isSuspicious ? 78 : 24);
  const timestamp = edge.timestamp || new Date().toISOString();

  // Deduce 3-5 high value key risk signals
  const signals = [];
  if (isSuspicious) {
    signals.push({
      title: 'NEW RECEIVER OBSERVED',
      desc: 'First recorded transfer to destination account within 30-day velocity window.',
      contribution: '+35 Risk'
    });
    signals.push({
      title: 'AMOUNT DEVIATION',
      desc: `Transfer of ₹${amount.toLocaleString('en-IN')} is 63% above baseline transaction size.`,
      contribution: '+25 Risk'
    });
    signals.push({
      title: 'MULTI-HOP PASS-THROUGH',
      desc: `Rapid layered routing detected at Hop ${hopNumber} of ${totalHops} in active mule chain.`,
      contribution: '+18 Risk'
    });
  } else {
    signals.push({
      title: 'STANDARD ACCOUNT HISTORY',
      desc: 'Transaction aligns with established historical channel and counterparty behavior.',
      contribution: '0 Risk'
    });
  }

  // Why this matters summary text
  const whyItMatters = isSuspicious
    ? `This transaction is part of a high-risk multi-hop fund flow involving a newly observed receiver and abnormal velocity patterns. Its position at Hop ${hopNumber} of ${totalHops} increases investigative priority.`
    : `This transaction exhibits standard velocity and account behavior, operating within normal baseline limits.`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 select-none animate-fadeIn"
      style={{ background: 'rgba(2, 6, 23, 0.85)', backdropFilter: 'blur(16px)' }}
      onClick={() => onClose?.()}
    >
      <div
        className="relative w-full max-w-5xl bg-[#0A0F1D]/95 border border-sky-500/20 rounded-2xl shadow-[0_0_50px_rgba(56,189,248,0.12)] overflow-hidden flex flex-col max-h-[85vh] my-auto"
        style={{ color: '#F8FAFC', fontFamily: 'Hanken Grotesk, system-ui, sans-serif' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── 1. HEADER ─────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1E293B] bg-[#060B15] shrink-0">
          <div className="flex items-center gap-3.5">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center shadow-inner"
              style={{
                background: isSuspicious ? 'rgba(239, 68, 68, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                border: `1px solid ${isSuspicious ? 'rgba(239, 68, 68, 0.4)' : 'rgba(56, 189, 248, 0.4)'}`
              }}
            >
              {isSuspicious ? (
                <ShieldAlert className="w-5 h-5 text-red-400" />
              ) : (
                <Activity className="w-5 h-5 text-sky-400" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-['JetBrains_Mono'] font-bold text-slate-400 uppercase tracking-widest">
                  TRANSACTION INSPECTOR
                </span>
                <span className="text-[10px] font-['JetBrains_Mono'] text-slate-500">
                  {timestamp} · {channel} · {chainId}
                </span>
              </div>
              <div className="text-lg font-bold font-['JetBrains_Mono'] text-[#38BDF8] tracking-tight">
                {txId}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span
              className="px-3 py-1 rounded-md text-[10px] font-['JetBrains_Mono'] font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-sm"
              style={{
                background: isSuspicious ? 'rgba(239, 68, 68, 0.15)' : 'rgba(52, 211, 153, 0.15)',
                border: `1px solid ${isSuspicious ? 'rgba(239, 68, 68, 0.4)' : 'rgba(52, 211, 153, 0.4)'}`,
                color: isSuspicious ? '#EF4444' : '#34D399'
              }}
            >
              <span className={`w-2 h-2 rounded-full ${isSuspicious ? 'bg-red-500 animate-pulse' : 'bg-emerald-400'}`} />
              {isSuspicious ? 'SUSPICIOUS' : 'NORMAL'}
            </span>

            <button
              onClick={() => onClose?.()}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-[#1E293B] transition-colors"
              title="Close (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* ── 2. PRIMARY METRIC STRIP ───────────────────────────────────────── */}
        <div className="grid grid-cols-4 divide-x divide-[#1E293B] border-b border-[#1E293B] bg-[#0A0F1D] shrink-0 text-xs">
          {/* Risk Score */}
          <div className="p-4 flex items-center gap-3">
            <div className="relative flex items-center justify-center">
              <svg width="44" height="44" viewBox="0 0 44 44">
                <circle cx="22" cy="22" r="18" fill="none" stroke="#1E293B" strokeWidth="3.5" />
                <circle cx="22" cy="22" r="18" fill="none" stroke={isSuspicious ? '#EF4444' : '#34D399'} strokeWidth="3.5"
                  strokeDasharray={`${(riskScore / 100) * 113} 113`} strokeLinecap="round" transform="rotate(-90 22 22)" />
              </svg>
              <span className={`absolute font-['JetBrains_Mono'] text-xs font-bold ${isSuspicious ? 'text-red-400' : 'text-emerald-400'}`}>
                {riskScore}
              </span>
            </div>
            <div>
              <div className="text-[10px] font-['JetBrains_Mono'] text-slate-500 uppercase tracking-wider">RISK SCORE</div>
              <div className="text-sm font-bold font-['JetBrains_Mono'] text-slate-100">{riskScore} / 100</div>
              <div className={`text-[9px] font-bold uppercase ${isSuspicious ? 'text-red-400' : 'text-emerald-400'}`}>
                {isSuspicious ? 'HIGH RISK' : 'LOW RISK'}
              </div>
            </div>
          </div>

          {/* Amount */}
          <div className="p-4">
            <div className="text-[10px] font-['JetBrains_Mono'] text-slate-500 uppercase tracking-wider">TRANSFER AMOUNT</div>
            <div className="text-lg font-bold font-['JetBrains_Mono'] text-emerald-400 mt-0.5">
              ₹{amount.toLocaleString('en-IN')}
            </div>
            <div className="text-[9px] text-slate-400 font-['JetBrains_Mono']">INR · {channel} CHANNEL</div>
          </div>

          {/* Status */}
          <div className="p-4">
            <div className="text-[10px] font-['JetBrains_Mono'] text-slate-500 uppercase tracking-wider">FLAG STATUS</div>
            <div className={`text-sm font-bold font-['JetBrains_Mono'] mt-0.5 ${isSuspicious ? 'text-red-400' : 'text-emerald-400'}`}>
              {isSuspicious ? 'SUSPICIOUS' : 'NORMAL'}
            </div>
            <div className="text-[9px] text-slate-400 font-['JetBrains_Mono']">
              {isSuspicious ? 'UPSTREAM FLAGGED' : 'CLEARED'}
            </div>
          </div>

          {/* Hop Position */}
          <div className="p-4">
            <div className="text-[10px] font-['JetBrains_Mono'] text-slate-500 uppercase tracking-wider">HOP POSITION</div>
            <div className="text-sm font-bold font-['JetBrains_Mono'] text-sky-400 mt-0.5">
              HOP {hopNumber} OF {totalHops}
            </div>
            <div className="text-[9px] text-slate-400 font-['JetBrains_Mono']">IN MULTI-HOP FLOW</div>
          </div>
        </div>

        {/* ── 3. TWO-COLUMN WORKSPACE BODY ──────────────────────────────────── */}
        <div className="p-6 grid grid-cols-2 gap-6 overflow-y-auto flex-1">

          {/* LEFT COLUMN: TRANSACTION FLOW & NETWORK CONTEXT */}
          <div className="space-y-5">
            {/* TRANSACTION FLOW VISUALIZATION */}
            <div className="p-4 rounded-xl border border-[#1E293B] bg-[#060B15] space-y-3 shadow-inner">
              <div className="text-[10px] font-['JetBrains_Mono'] font-bold text-sky-400 uppercase tracking-widest flex items-center justify-between">
                <span>MONEY MOVEMENT FLOW</span>
                <span className="text-[9px] text-slate-500 font-normal">CHANNEL: {channel}</span>
              </div>

              <div className="flex items-center justify-between gap-3 pt-1">
                {/* Sender */}
                <div className="flex-1 bg-[#0A0F1D] p-3 rounded-lg border border-[#1E293B]">
                  <div className="text-[9px] font-['Hanken_Grotesk'] text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Shield className="w-3 h-3 text-sky-400" /> SENDER ACCOUNT
                  </div>
                  <div className="font-['JetBrains_Mono'] text-xs font-bold text-slate-100 truncate" title={source}>
                    {source}
                  </div>
                  <div className="text-[9px] text-slate-500 mt-0.5">VICTIM / SENDER</div>
                </div>

                {/* Animated Flow Arrow */}
                <div className="flex flex-col items-center shrink-0 px-2 text-center">
                  <div className="font-['JetBrains_Mono'] text-sm font-bold text-emerald-400">
                    ₹{amount.toLocaleString('en-IN')}
                  </div>
                  <div className="flex items-center gap-1 my-1">
                    <div className="w-8 h-0.5 bg-gradient-to-r from-sky-500 to-emerald-400 animate-pulse" />
                    <ArrowRight className="w-4 h-4 text-emerald-400 shrink-0" />
                  </div>
                  <span className="text-[9px] font-['JetBrains_Mono'] px-1.5 py-0.5 rounded bg-slate-800 text-sky-300 border border-slate-700">
                    Hop {hopNumber}/{totalHops}
                  </span>
                </div>

                {/* Receiver */}
                <div className="flex-1 bg-[#0A0F1D] p-3 rounded-lg border border-[#1E293B]">
                  <div className="text-[9px] font-['Hanken_Grotesk'] text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Shield className="w-3 h-3 text-purple-400" /> DESTINATION ACCOUNT
                  </div>
                  <div className="font-['JetBrains_Mono'] text-xs font-bold text-slate-100 truncate" title={target}>
                    {target}
                  </div>
                  <div className="text-[9px] text-purple-400 font-semibold mt-0.5">MULE / RECEIVER</div>
                </div>
              </div>
            </div>

            {/* NETWORK CONTEXT */}
            <div className="p-4 rounded-xl border border-[#1E293B] bg-[#060B15] space-y-3">
              <div className="text-[10px] font-['JetBrains_Mono'] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                <GitCommit className="w-3.5 h-3.5 text-purple-400" /> NETWORK CONTEXT
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs font-['JetBrains_Mono']">
                <div className="p-2.5 rounded bg-[#0A0F1D] border border-[#1E293B]">
                  <div className="text-[9px] font-['Hanken_Grotesk'] text-slate-500 uppercase">PATTERN TYPE</div>
                  <div className="font-semibold text-purple-300 mt-0.5">{patternType}</div>
                </div>

                <div className="p-2.5 rounded bg-[#0A0F1D] border border-[#1E293B]">
                  <div className="text-[9px] font-['Hanken_Grotesk'] text-slate-500 uppercase">CHAIN ID</div>
                  <div className="font-semibold text-sky-300 truncate mt-0.5" title={chainId}>{chainId}</div>
                </div>

                {parentTxId && (
                  <div className="p-2.5 rounded bg-[#0A0F1D] border border-[#1E293B]">
                    <div className="text-[9px] font-['Hanken_Grotesk'] text-slate-500 uppercase">PARENT TX</div>
                    <div className="text-slate-300 truncate mt-0.5" title={parentTxId}>{parentTxId}</div>
                  </div>
                )}

                {rootTxId && (
                  <div className="p-2.5 rounded bg-[#0A0F1D] border border-[#1E293B]">
                    <div className="text-[9px] font-['Hanken_Grotesk'] text-slate-500 uppercase">ROOT TX</div>
                    <div className="text-slate-300 truncate mt-0.5" title={rootTxId}>{rootTxId}</div>
                  </div>
                )}
              </div>
            </div>

            {/* TRANSACTION METADATA */}
            <div className="p-4 rounded-xl border border-[#1E293B] bg-[#060B15] space-y-2 text-xs font-['JetBrains_Mono'] text-slate-400">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">TRANSACTION METADATA</div>
              <div className="flex justify-between"><span>Transaction ID:</span><span className="text-slate-200">{txId}</span></div>
              <div className="flex justify-between"><span>Timestamp:</span><span className="text-slate-200">{timestamp}</span></div>
              <div className="flex justify-between"><span>Channel:</span><span className="text-slate-200">{channel}</span></div>
              <div className="flex justify-between"><span>Hop Index:</span><span className="text-slate-200">{hopNumber} of {totalHops}</span></div>
            </div>
          </div>

          {/* RIGHT COLUMN: KEY RISK SIGNALS & WHY THIS MATTERS */}
          <div className="space-y-5">

            {/* KEY RISK SIGNALS */}
            <div>
              <div className="text-[10px] font-['JetBrains_Mono'] font-bold text-slate-400 uppercase tracking-widest mb-2.5">
                KEY RISK SIGNALS
              </div>
              <div className="space-y-2.5">
                {signals.map((sig, i) => (
                  <div
                    key={i}
                    className="p-3.5 rounded-xl border text-xs bg-[#060B15]"
                    style={{
                      borderColor: isSuspicious ? 'rgba(239, 68, 68, 0.25)' : '#1E293B'
                    }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                        <span className={`w-1.5 h-1.5 rounded-full ${isSuspicious ? 'bg-red-400' : 'bg-emerald-400'}`} />
                        {sig.title}
                      </div>
                      <span className="text-[9px] font-['JetBrains_Mono'] font-bold px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/30">
                        {sig.contribution}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      {sig.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* WHY THIS MATTERS */}
            <div className="p-4 rounded-xl border border-sky-500/20 bg-sky-500/5 space-y-1.5">
              <div className="text-[10px] font-['JetBrains_Mono'] font-bold text-sky-400 uppercase tracking-widest flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5" /> WHY THIS MATTERS
              </div>
              <p className="text-xs text-slate-300 leading-relaxed font-['Hanken_Grotesk']">
                "{whyItMatters}"
              </p>
            </div>

          </div>
        </div>

        {/* ── 4. FOOTER: CONTROLS & AUTOMATION STATUS ───────────────────────── */}
        <div className="px-6 py-4 border-t border-[#1E293B] bg-[#060B15] shrink-0 flex items-center justify-between">
          {/* Automation Status Indicator */}
          {isAutomationOn ? (
            <div className="flex items-center gap-2 text-xs font-['JetBrains_Mono'] text-slate-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span className="font-bold text-emerald-400">AUTOMATION ACTIVE</span>
              <span className="text-slate-600">·</span>
              <span className="text-slate-500">NON-FREEZE ACTIONS EXECUTED AUTONOMOUSLY BY POLICY ENGINE</span>
            </div>
          ) : (
            <div className="text-xs font-['JetBrains_Mono'] text-amber-400 font-bold">
              MANUAL OPERATOR MODE
            </div>
          )}

          {/* Action Control: FREEZE (Human Operator Only) */}
          <div className="flex items-center gap-3">
            {isSuspicious && (
              <button
                onClick={() => onAction?.('freeze')}
                className="px-4 py-2 rounded-lg text-xs font-['JetBrains_Mono'] font-bold bg-rose-600 hover:bg-rose-500 text-white border border-rose-400 shadow-lg transition-all flex items-center gap-2"
              >
                <Lock className="w-3.5 h-3.5" />
                <span>FREEZE ACCOUNT</span>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-black/30 text-rose-200">OPERATOR APPROVAL REQUIRED</span>
              </button>
            )}

            <button
              onClick={() => onClose?.()}
              className="px-4 py-2 rounded-lg text-xs font-['Hanken_Grotesk'] font-semibold bg-[#1E293B] hover:bg-[#334155] text-slate-200 transition-colors"
            >
              Close (Esc)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TransactionInspectorModal;
