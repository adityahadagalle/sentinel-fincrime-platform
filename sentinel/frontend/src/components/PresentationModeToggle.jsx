import React from 'react';
import { Bell, BellOff, Presentation } from 'lucide-react';
import { usePresentationMode } from '../hooks/usePresentationMode';

/**
 * Compact system control toggle for Presentation Mode.
 * 
 * States:
 * - OFF → Alerts visible (Default alerting)
 * - ON  → Popups suppressed (Disruptive pop-up notifications muted)
 */
const PresentationModeToggle = () => {
  const { isPresentationMode, togglePresentationMode } = usePresentationMode();

  return (
    <div className="space-y-1.5 font-sans">
      <button
        type="button"
        id="presentation-mode-toggle"
        onClick={togglePresentationMode}
        className={`w-full flex items-center justify-between px-3 py-2 rounded-xl font-mono text-xs font-bold transition-all border shadow-sm select-none focus:outline-none focus:ring-2 focus:ring-amber-500/40 ${
          isPresentationMode
            ? 'bg-amber-950/70 border-amber-500/80 text-amber-300 shadow-amber-950/50 hover:bg-amber-900/80'
            : 'bg-slate-900/90 border-slate-700/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
        }`}
        title={isPresentationMode ? 'Disable Presentation Mode (Show popups)' : 'Enable Presentation Mode (Suppress popups)'}
      >
        <div className="flex items-center gap-2">
          {isPresentationMode ? (
            <BellOff className="w-4 h-4 text-amber-400 shrink-0" />
          ) : (
            <Presentation className="w-4 h-4 text-slate-400 shrink-0" />
          )}
          <span className="tracking-tight">Presentation Mode</span>
        </div>

        <span
          className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-mono tracking-wider font-semibold ${
            isPresentationMode
              ? 'bg-amber-500/25 text-amber-300 border border-amber-500/40'
              : 'bg-slate-800 text-slate-400 border border-slate-700'
          }`}
        >
          {isPresentationMode ? 'ON' : 'OFF'}
        </span>
      </button>

      <div className="px-1 flex items-center justify-between text-[9px] font-mono select-none">
        <span className={isPresentationMode ? 'text-amber-400 font-semibold' : 'text-slate-500'}>
          {isPresentationMode ? 'Popups suppressed' : 'Alerts visible'}
        </span>
        {isPresentationMode && (
          <span className="flex items-center gap-1 text-amber-300/90 font-bold uppercase tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            QUIET UI
          </span>
        )}
      </div>
    </div>
  );
};

export default PresentationModeToggle;
