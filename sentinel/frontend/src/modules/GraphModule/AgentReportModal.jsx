import React, { useEffect } from 'react';
import { X, FileText, Cpu, Code } from 'lucide-react';
import AnalystEvidenceViewer from '../../components/AnalystEvidenceViewer';

const AgentReportModal = ({ report, onClose }) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!report) return null;

  const { title, stage, color, data } = report;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 select-none animate-fadeIn"
      style={{ background: 'rgba(2, 6, 23, 0.85)', backdropFilter: 'blur(12px)' }}
      onClick={() => onClose?.()}
    >
      <div
        className="relative w-full max-w-4xl bg-[#0F172A] border border-[#1E293B] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[88vh]"
        style={{ color: '#F8FAFC', fontFamily: 'Hanken Grotesk, system-ui, sans-serif' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── HEADER ──────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1E293B] bg-[#0A0F17] shrink-0">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: `${color || '#38BDF8'}18`, border: `1px solid ${color || '#38BDF8'}40` }}
            >
              <FileText className="w-5 h-5" style={{ color: color || '#38BDF8' }} />
            </div>
            <div>
              <div className="text-[10px] font-['JetBrains_Mono'] font-bold text-slate-500 uppercase tracking-widest">
                UPSTREAM AGENT REPORT WORKSPACE
              </div>
              <div className="text-base font-bold font-['JetBrains_Mono'] text-[#38BDF8]">
                {title || 'AGENT REPORT'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-[9px] font-['JetBrains_Mono'] px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold uppercase">
              STATUS: COMPLETED
            </span>
            <button
              onClick={() => onClose?.()}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-[#1E293B] transition-colors"
              title="Close Report (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* ── BODY ────────────────────────────────────────────────────────── */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1 text-xs">
          <AnalystEvidenceViewer stageKey={stage} data={data} status="COMPLETED" title={title} />
        </div>

        {/* ── FOOTER ──────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-[#1E293B] bg-[#0A0F17] shrink-0">
          <div className="text-[10px] font-['JetBrains_Mono'] text-slate-500">
            DETERMINISTIC INVESTIGATION PIPELINE · ANALYST EVIDENCE WORKSPACE
          </div>
          <button
            onClick={() => onClose?.()}
            className="px-4 py-1.5 rounded-lg text-xs font-['Hanken_Grotesk'] font-semibold bg-[#1E293B] hover:bg-[#334155] text-slate-200 transition-colors"
          >
            Close (Esc)
          </button>
        </div>
      </div>
    </div>
  );
};

export default AgentReportModal;
