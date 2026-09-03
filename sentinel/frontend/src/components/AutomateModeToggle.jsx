import React, { useState, useEffect } from 'react';
import { Bot, ShieldAlert, CheckCircle2, Lock, X, AlertTriangle } from 'lucide-react';

const AutomateModeToggle = () => {
  const [automateMode, setAutomateMode] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [loading, setLoading] = useState(false);

  // Fetch initial mode state from backend
  useEffect(() => {
    const fetchMode = async () => {
      try {
        const res = await fetch('/automation-mode').catch(() => fetch('http://localhost:8000/automation-mode'));
        const data = await res.json();
        setAutomateMode(Boolean(data.automate_mode));
      } catch (err) {
        console.error('Failed to fetch automation mode state:', err);
      }
    };
    fetchMode();

    const handleModeChange = (e) => {
      if (e.detail && e.detail.automate_mode !== undefined) {
        setAutomateMode(Boolean(e.detail.automate_mode));
      }
    };

    window.addEventListener('sentinel_automation_mode_changed', handleModeChange);
    return () => {
      window.removeEventListener('sentinel_automation_mode_changed', handleModeChange);
    };
  }, []);

  const handleToggleClick = () => {
    if (!automateMode) {
      setShowConfirmModal(true);
    } else {
      updateMode(false);
    }
  };

  const updateMode = async (enabled) => {
    setLoading(true);
    try {
      let res;
      try {
        res = await fetch('/automation-mode', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled, operator_id: 'OPERATOR_ADMIN' })
        });
      } catch {
        res = await fetch('http://localhost:8000/automation-mode', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled, operator_id: 'OPERATOR_ADMIN' })
        });
      }
      const data = await res.json();
      if (data.status === 'success') {
        setAutomateMode(enabled);
        window.dispatchEvent(new CustomEvent('sentinel_automation_mode_changed', { detail: { automate_mode: enabled } }));
      }
    } catch (err) {
      console.error('Failed to update automation mode:', err);
    } finally {
      setLoading(false);
      setShowConfirmModal(false);
    }
  };


  return (
    <>
      {/* Global Control Button */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleToggleClick}
          disabled={loading}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-xl font-mono text-xs font-bold transition-all border shadow-sm select-none ${
            automateMode
              ? 'bg-emerald-950/80 border-emerald-500/80 text-emerald-300 shadow-emerald-950/50 hover:bg-emerald-900/90'
              : 'bg-slate-900/90 border-slate-700/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
          title="Toggle System Automate Mode"
        >
          <div className="flex items-center gap-2">
            <Bot className={`w-4 h-4 ${automateMode ? 'text-emerald-400 animate-pulse' : 'text-slate-500'}`} />
            <span>{automateMode ? '● AUTOMATION ACTIVE' : '○ AUTOMATION OFF'}</span>
          </div>
          <span
            className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-mono tracking-wider ${
              automateMode
                ? 'bg-emerald-500/25 text-emerald-300 border border-emerald-500/40'
                : 'bg-slate-800 text-slate-400 border border-slate-700'
            }`}
          >
            {automateMode ? 'ON' : 'OFF'}
          </span>
        </button>
      </div>


      {/* Operator Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-[120] bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 select-none animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 font-sans relative">
            <button
              onClick={() => setShowConfirmModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
              <div className="p-2 bg-emerald-500/20 text-emerald-400 rounded-xl border border-emerald-500/30">
                <Bot className="w-6 h-6 animate-pulse" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-100 font-mono uppercase tracking-wide">
                  ENABLE AUTOMATE MODE
                </h3>
                <p className="text-xs text-slate-400 font-sans">
                  Operator Confirmation Required
                </p>
              </div>
            </div>

            <div className="space-y-3 text-xs text-slate-300 leading-relaxed">
              <div className="p-3 bg-emerald-950/40 border border-emerald-500/30 rounded-xl space-y-1.5">
                <div className="font-mono font-bold text-emerald-300 uppercase flex items-center gap-1.5 text-[11px]">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  PERMITTED AUTOMATED ACTIONS
                </div>
                <p className="text-slate-300 text-[11px]">
                  When active, SENTINEL will automatically execute allowed monitoring & escalation actions:
                </p>
                <div className="flex flex-wrap gap-1 pt-1 font-mono text-[10px]">
                  {['MONITOR', 'ENHANCED_MONITORING', 'ESCALATE_ANALYST_REVIEW', 'URGENT_ANALYST_REVIEW'].map((act) => (
                    <span key={act} className="px-2 py-0.5 rounded bg-emerald-900/60 border border-emerald-700/60 text-emerald-200">
                      {act}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-3 bg-rose-950/40 border border-rose-500/30 rounded-xl space-y-1.5">
                <div className="font-mono font-bold text-rose-300 uppercase flex items-center gap-1.5 text-[11px]">
                  <Lock className="w-4 h-4 text-rose-400 shrink-0" />
                  RESTRICTED FINANCIAL ACTIONS BLOCK
                </div>
                <p className="text-rose-200/90 text-[11px]">
                  Forbidden high-impact actions (FREEZE, BLOCK, FILE_STR, CLOSE_ACCOUNT, REJECT_TRANSACTION) will <strong>NEVER</strong> be executed automatically.
                </p>
                <p className="text-amber-300/90 font-mono text-[10px]">
                  Status will set to: REQUIRES_HUMAN_APPROVAL
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-mono font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-700"
              >
                CANCEL
              </button>
              <button
                type="button"
                onClick={() => updateMode(true)}
                disabled={loading}
                className="px-4 py-2 rounded-xl text-xs font-mono font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/60 flex items-center gap-1.5"
              >
                {loading ? 'CONFIRMING...' : 'CONFIRM & ENABLE'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AutomateModeToggle;
