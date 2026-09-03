import React from 'react';

/**
 * RiskBadge — Enterprise SOC severity badge.
 * Recreated from friend's exact design language:
 * - rounded-full pill badge
 * - score number
 * - vertical separator border
 * - uppercase severity label
 */
const RiskBadge = ({ score, showLabel = true, className = "" }) => {
  const getRiskDetails = (s) => {
    if (s >= 85) {
      return {
        label: 'CRITICAL',
        styles: 'bg-rose-500/15 text-rose-400 border-rose-500/30'
      };
    }
    if (s >= 70) {
      return {
        label: 'HIGH',
        styles: 'bg-orange-500/15 text-orange-400 border-orange-500/30'
      };
    }
    if (s >= 40) {
      return {
        label: 'MEDIUM',
        styles: 'bg-amber-500/15 text-amber-400 border-amber-500/30'
      };
    }
    return {
      label: 'LOW',
      styles: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
    };
  };

  const { label, styles } = getRiskDetails(Number(score || 0));

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold border shrink-0 ${styles} ${className}`}
    >
      <span>{score}</span>
      {showLabel && (
        <span className="text-[9px] font-sans font-semibold tracking-wider opacity-90 border-l border-current/30 pl-1.5 uppercase">
          {label}
        </span>
      )}
    </div>
  );
};

export default RiskBadge;
