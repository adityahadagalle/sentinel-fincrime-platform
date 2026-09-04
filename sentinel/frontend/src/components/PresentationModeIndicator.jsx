import React from 'react';
import { BellOff, X } from 'lucide-react';
import { usePresentationMode } from '../hooks/usePresentationMode';

/**
 * Non-intrusive floating indicator pill displayed when Presentation Mode is active.
 * Provides subtle, persistent awareness to presenters that popups are suppressed,
 * along with a quick-exit control.
 */
const PresentationModeIndicator = () => {
  const { isPresentationMode, setPresentationMode } = usePresentationMode();

  if (!isPresentationMode) return null;

  return (
    <div
      id="presentation-mode-indicator"
      className="fixed top-3 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-slate-950/90 border border-amber-500/50 text-amber-300 text-[11px] font-mono font-bold shadow-xl shadow-amber-950/40 backdrop-blur-md animate-in fade-in slide-in-from-top-2 duration-200 select-none"
    >
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
      </span>

      <div className="flex items-center gap-1.5">
        <BellOff className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        <span className="tracking-wide">PRESENTATION MODE</span>
      </div>

      <span className="text-[9px] font-mono text-amber-200/70 border-l border-amber-500/30 pl-2 uppercase">
        Popups Suppressed
      </span>

      <button
        type="button"
        onClick={() => setPresentationMode(false)}
        className="ml-1 flex items-center gap-1 text-[9px] font-mono px-2 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/30 transition-colors"
        title="Exit Presentation Mode"
        aria-label="Exit Presentation Mode"
      >
        <span>EXIT</span>
        <X className="w-2.5 h-2.5" />
      </button>
    </div>
  );
};

export default PresentationModeIndicator;
