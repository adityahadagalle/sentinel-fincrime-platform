import React, { useEffect } from 'react';
import { X, Shield, ArrowUpRight, ArrowDownLeft, Layers, AlertTriangle } from 'lucide-react';

const EntityDetailModal = ({ node, onClose }) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!node) return null;

  const accountId = node.accountId || node.id || 'ACC-UNKNOWN';
  const nodeType = (node.node_type || node.account_type || 'ACCOUNT').toUpperCase();
  const layer = node.layer || 0;
  const status = (node.status || 'ACTIVE').toUpperCase();
  const inboundTotal = Number(node.total_inbound || 0);
  const outboundTotal = Number(node.total_outbound || 0);
  const balance = Number(node.balance || 0);
  const riskScore = Number(node.risk_score || 0);

  const typeColorMap = {
    VICTIM: '#3B82F6',
    SOURCE: '#3B82F6',
    MULE: '#EF4444',
    COLLECTOR: '#F59E0B',
    CASHOUT: '#DC2626',
    CRYPTO: '#A78BFA',
    MERCHANT: '#34D399'
  };

  const badgeColor = typeColorMap[nodeType] || '#38BDF8';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 select-none animate-fadeIn"
      style={{ background: 'rgba(2, 6, 23, 0.75)', backdropFilter: 'blur(8px)' }}
      onClick={() => onClose?.()}
    >
      <div
        className="relative w-full max-w-lg bg-[#0F172A] border border-[#1E293B] rounded-2xl shadow-2xl overflow-hidden"
        style={{ color: '#F8FAFC', fontFamily: 'Hanken Grotesk, system-ui, sans-serif' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── MODAL HEADER ────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1E293B] bg-[#0A0F17]">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center font-['JetBrains_Mono'] font-bold text-xs"
              style={{
                background: `${badgeColor}18`,
                border: `1px solid ${badgeColor}50`,
                color: badgeColor
              }}
            >
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[10px] font-['JetBrains_Mono'] font-semibold text-slate-500 uppercase tracking-widest">
                ENTITY DETAILS
              </div>
              <div className="text-base font-bold font-['JetBrains_Mono'] text-[#38BDF8]">
                {accountId}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span
              className="px-2.5 py-1 rounded text-[10px] font-['JetBrains_Mono'] font-bold uppercase tracking-wider"
              style={{
                background: `${badgeColor}18`,
                border: `1px solid ${badgeColor}40`,
                color: badgeColor
              }}
            >
              {nodeType}
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

        {/* ── MODAL BODY ──────────────────────────────────────────────────── */}
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-3 rounded-xl border border-[#1E293B] bg-[#0B132B]">
              <div className="text-[9px] font-['Hanken_Grotesk'] text-slate-500 uppercase tracking-wider mb-1">
                LAYER / HOP
              </div>
              <div className="font-['JetBrains_Mono'] text-sm font-bold text-slate-200">
                Layer {layer}
              </div>
            </div>

            <div className="p-3 rounded-xl border border-[#1E293B] bg-[#0B132B]">
              <div className="text-[9px] font-['Hanken_Grotesk'] text-slate-500 uppercase tracking-wider mb-1">
                STATUS
              </div>
              <div className="font-['JetBrains_Mono'] text-sm font-bold text-amber-400">
                {status}
              </div>
            </div>

            <div className="p-3 rounded-xl border border-[#1E293B] bg-[#0B132B]">
              <div className="text-[9px] font-['Hanken_Grotesk'] text-slate-500 uppercase tracking-wider mb-1">
                RISK SCORE
              </div>
              <div className="font-['JetBrains_Mono'] text-sm font-bold text-red-400">
                {riskScore > 0 ? `${riskScore}/100` : 'N/A'}
              </div>
            </div>
          </div>

          {/* FINANCIAL TOTALS */}
          <div className="p-4 rounded-xl border border-[#1E293B] bg-[#0B132B] space-y-3">
            <div className="text-[10px] font-['JetBrains_Mono'] font-semibold text-slate-500 uppercase tracking-widest">
              FINANCIAL ACTIVITY
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-[#0A0F17] border border-[#1E293B]">
                <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  <ArrowDownLeft className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[9px] text-slate-500 uppercase">Total Inbound</div>
                  <div className="font-['JetBrains_Mono'] text-xs font-bold text-emerald-400">
                    ₹{inboundTotal.toLocaleString('en-IN')}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-lg bg-[#0A0F17] border border-[#1E293B]">
                <div className="p-2 rounded bg-red-500/10 border border-red-500/30 text-red-400">
                  <ArrowUpRight className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[9px] text-slate-500 uppercase">Total Outbound</div>
                  <div className="font-['JetBrains_Mono'] text-xs font-bold text-red-400">
                    ₹{outboundTotal.toLocaleString('en-IN')}
                  </div>
                </div>
              </div>
            </div>

            {balance > 0 && (
              <div className="flex justify-between items-center pt-2 border-t border-[#1E293B] text-xs">
                <span className="text-slate-500">Current Balance</span>
                <span className="font-['JetBrains_Mono'] font-bold text-slate-200">
                  ₹{balance.toLocaleString('en-IN')}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* ── MODAL FOOTER ────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-[#1E293B] bg-[#0A0F17]">
          <div className="text-[10px] font-['JetBrains_Mono'] text-slate-500">
            ENTITY INSPECTION · GRAPH CONTEXT PRESERVED
          </div>
          <button
            onClick={() => onClose?.()}
            className="px-4 py-1.5 rounded text-xs font-['Hanken_Grotesk'] font-semibold bg-[#1E293B] hover:bg-[#334155] text-slate-200 transition-colors"
          >
            Close (Esc)
          </button>
        </div>
      </div>
    </div>
  );
};

export default EntityDetailModal;
