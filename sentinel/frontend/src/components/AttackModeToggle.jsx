import React, { useState, useEffect, useRef } from 'react';
import { ShieldAlert, Zap, CheckCircle2 } from 'lucide-react';
import { getRole } from '../roleStore';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const AttackModeToggle = () => {
  const [isAttack, setIsAttack] = useState(window.__SENTINEL_ATTACK_MODE__ || false);
  const role = getRole();
  const isViewer = role !== 'admin';
  const intervalRef = useRef(null);

  const fireBurst = async () => {
    try {
      await fetch(`${API_BASE}/attack-mode`, { method: 'POST' });
    } catch (e) {
      console.error('[SENTINEL] Attack mode burst failed:', e);
    }
  };

  const toggleMode = async () => {
    if (isViewer) return;
    const newState = !isAttack;
    setIsAttack(newState);
    window.__SENTINEL_ATTACK_MODE__ = newState;
    window.dispatchEvent(new CustomEvent('sentinel_mode_change', { detail: newState }));

    if (newState) {
      // Fire immediately, then repeat every 30s
      await fireBurst();
      intervalRef.current = setInterval(fireBurst, 30000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  return (
    <div className={`space-y-2.5 ${isViewer ? 'opacity-60 pointer-events-none' : ''}`}>
      {isAttack && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 animate-pulse">
          <ShieldAlert className="w-3.5 h-3.5 shrink-0 text-rose-400" />
          <span className="text-[10px] font-bold uppercase tracking-wider font-mono">
            Simulated Burst Active
          </span>
        </div>
      )}
      
      <div className="flex items-center justify-between p-1 bg-muted/40 border border-border/80 rounded-xl">
        <button
          onClick={toggleMode}
          disabled={isViewer}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all duration-200 ${
            !isAttack
              ? 'bg-slate-800 text-emerald-400 shadow-sm border border-slate-700/60'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <CheckCircle2 className="w-3 h-3" />
          <span>NORMAL</span>
        </button>

        <button
          onClick={toggleMode}
          disabled={isViewer}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all duration-200 ${
            isAttack
              ? 'bg-rose-600 text-white shadow-md shadow-rose-600/30 border border-rose-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Zap className="w-3 h-3 fill-current" />
          <span>ATTACK</span>
        </button>
      </div>
    </div>
  );
};

export default AttackModeToggle;

