import React, { useEffect } from 'react';
import { X, Layers, ShieldAlert, ArrowUpRight, ArrowDownLeft, Lock, CheckCircle2, ChevronRight, Maximize2 } from 'lucide-react';
import { maskAccount } from '../../utils/maskAccount';
import { getRole } from '../../roleStore';

const ClusterDetailModal = ({ clusterNode, onClose, onInspectIndividualNode, onExpandCluster }) => {
  const role = getRole();

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!clusterNode) return null;

  const clusterNodes = clusterNode.clusterNodes || [];
  const clusterType = (clusterNode.cluster_type || clusterNode.type || 'MULE').toUpperCase();
  const label = clusterNode.label || clusterNode.displayLabel || 'CLUSTERED ENTITIES';
  const totalAmount = Number(clusterNode.total_inbound || clusterNode.total_outbound || 0);

  const isMule = clusterType.includes('MULE');
  const isVictim = clusterType.includes('VICTIM');
  const isExit = clusterType.includes('CASH') || clusterType.includes('EXIT');

  const themeColor = isMule ? '#EF4444' : isVictim ? '#3B82F6' : isExit ? '#F59E0B' : '#A855F7';
  const themeBg = isMule ? 'bg-red-950/40 border-red-500/40 text-red-400'
    : isVictim ? 'bg-blue-950/40 border-blue-500/40 text-blue-400'
    : 'bg-amber-950/40 border-amber-500/40 text-amber-400';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 select-none animate-fadeIn"
      style={{ background: 'rgba(2, 6, 23, 0.85)', backdropFilter: 'blur(8px)' }}
      onClick={() => onClose?.()}
    >
      <div
        className="relative w-full max-w-xl bg-[#0B1322] border border-[#1E2E4A] rounded-2xl shadow-2xl overflow-hidden font-['JetBrains_Mono'] text-slate-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── HEADER ── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1E2E4A] bg-[#070D18]">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm shadow-inner"
              style={{
                background: `${themeColor}20`,
                border: `1px solid ${themeColor}60`,
                color: themeColor
              }}
            >
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold tracking-tight text-white">{label}</h3>
                <span className={`text-[9px] font-bold px-2 py-0.5 rounded border uppercase ${themeBg}`}>
                  {clusterNodes.length} ACCOUNTS AGGREGATED
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Visual cluster grouping {clusterNodes.length} sibling entities in the money flow
              </p>
            </div>
          </div>
          <button
            onClick={() => onClose?.()}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* ── SUMMARY STATS ── */}
        <div className="grid grid-cols-3 gap-3 p-4 bg-[#070D1A]/60 border-b border-[#1A2840] text-xs">
          <div className="bg-[#0D182E] border border-[#1E2E4A] rounded-lg p-2.5">
            <span className="text-[9px] text-slate-400 uppercase tracking-wider block">Aggregated Volume</span>
            <span className="text-sm font-bold text-amber-400 mt-0.5 block">
              ₹{totalAmount.toLocaleString('en-IN')}
            </span>
          </div>
          <div className="bg-[#0D182E] border border-[#1E2E4A] rounded-lg p-2.5">
            <span className="text-[9px] text-slate-400 uppercase tracking-wider block">Max Assessed Risk</span>
            <span className="text-sm font-bold text-red-400 mt-0.5 block">
              {clusterNode.risk_score || 95}/100
            </span>
          </div>
          <div className="bg-[#0D182E] border border-[#1E2E4A] rounded-lg p-2.5">
            <span className="text-[9px] text-slate-400 uppercase tracking-wider block">Network Hop</span>
            <span className="text-sm font-bold text-sky-400 mt-0.5 block">
              Layer {clusterNode.layer || 2}
            </span>
          </div>
        </div>

        {/* ── UNDERLYING ACCOUNTS LIST ── */}
        <div className="p-4 max-h-72 overflow-y-auto space-y-2">
          <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-2">
            Underlying Accounts in this Cluster ({clusterNodes.length}):
          </div>

          {clusterNodes.map((acc, idx) => {
            const rawId = String(acc.id || acc.accountId || `ACC-${idx}`);
            const displayId = role === 'admin' ? rawId : maskAccount(rawId);
            const risk = acc.risk_score || (isMule ? 95 : 60);
            const isFrozen = (acc.status || '').toLowerCase() === 'frozen';

            return (
              <div
                key={rawId}
                className="flex items-center justify-between p-3 rounded-lg bg-[#08101E] border border-[#1A2840] hover:border-sky-500/50 hover:bg-[#0E1B33] transition-all group cursor-pointer"
                onClick={() => {
                  onInspectIndividualNode?.(acc);
                  onClose?.();
                }}
              >
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: themeColor }} />
                  <div>
                    <div className="text-xs font-bold text-white flex items-center gap-2">
                      <span>{displayId}</span>
                      {isFrozen && (
                        <span className="px-1.5 py-0.2 rounded text-[8px] bg-red-950 text-red-400 border border-red-600/40 flex items-center gap-1">
                          <Lock className="w-2 h-2" /> FROZEN
                        </span>
                      )}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      Type: <span className="text-slate-300 font-semibold uppercase">{acc.type || clusterType}</span>
                      {acc.layer !== undefined && ` · Hop Layer ${acc.layer}`}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <span className="text-[9px] text-slate-500 uppercase block">Risk Score</span>
                    <span className="text-xs font-bold text-red-400">{risk}/100</span>
                  </div>
                  <button
                    className="p-1.5 rounded bg-[#101D36] border border-[#20345A] group-hover:bg-sky-600 group-hover:text-white transition-all text-slate-300 text-[10px] flex items-center gap-1"
                    title="Inspect Individual Entity"
                  >
                    <span>Inspect</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* ── FOOTER ACTIONS ── */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-[#1E2E4A] bg-[#070D18]">
          <span className="text-[11px] text-slate-400">
            Click any account above to open its deep forensic dossier.
          </span>
          <div className="flex items-center gap-2">
            {onExpandCluster && (
              <button
                onClick={() => {
                  onExpandCluster();
                  onClose?.();
                }}
                className="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-[#142340] hover:bg-[#1E3560] border border-[#224070] text-sky-400 flex items-center gap-1.5 transition-all"
              >
                <Maximize2 className="w-3.5 h-3.5" />
                <span>Expand in Graph</span>
              </button>
            )}
            <button
              onClick={() => onClose?.()}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-[#1A2640] hover:bg-[#25365A] text-slate-200 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClusterDetailModal;
