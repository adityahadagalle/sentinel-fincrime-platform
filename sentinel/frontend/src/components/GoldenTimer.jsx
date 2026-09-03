import React from 'react';
import { twMerge } from 'tailwind-merge';
import { Clock } from 'lucide-react';

const GoldenTimer = ({ minutes, className = "" }) => {
  const getTimerColor = (m) => {
    if (m > 15) return "text-emerald-400";
    if (m >= 5) return "text-amber-400";
    return "text-rose-400";
  };

  const formatTime = (m) => {
    const totalSeconds = Math.max(0, m * 60);
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className={twMerge("font-mono font-semibold text-xs flex items-center gap-1.5 shrink-0", getTimerColor(minutes), className)}>
      <Clock className="w-3.5 h-3.5 opacity-80" />
      <span>{formatTime(minutes)}</span>
    </div>
  );
};

export default GoldenTimer;

