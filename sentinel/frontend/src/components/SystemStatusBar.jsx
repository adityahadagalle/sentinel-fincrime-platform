import React, { useState, useEffect } from 'react';
import { RefreshCw, Wifi, WifiOff, AlertTriangle } from 'lucide-react';

const SystemStatusBar = ({ status }) => {
  const [lastEventTime, setLastEventTime] = useState(0);

  useEffect(() => {
    // Reset timer on status change or simulation heartbeat
    setLastEventTime(0);
    const interval = setInterval(() => {
      setLastEventTime((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [status]);

  const getStatusConfig = (s) => {
    switch (s) {
      case 'LIVE':
        return {
          dotColor: 'bg-emerald-500',
          textColor: 'text-emerald-400',
          borderColor: 'border-emerald-500/20 bg-emerald-500/5',
          text: 'LIVE',
          pulse: true,
          icon: Wifi
        };
      case 'POLLING':
        return {
          dotColor: 'bg-amber-500',
          textColor: 'text-amber-400',
          borderColor: 'border-amber-500/20 bg-amber-500/5',
          text: 'POLLING',
          pulse: false,
          icon: RefreshCw
        };
      case 'RECONNECTING':
        return {
          dotColor: 'bg-amber-500',
          textColor: 'text-amber-400',
          borderColor: 'border-amber-500/30 bg-amber-500/10',
          text: 'RECONNECTING',
          pulse: true,
          icon: RefreshCw,
          spin: true
        };
      case 'OFFLINE':
        return {
          dotColor: 'bg-rose-500',
          textColor: 'text-rose-400',
          borderColor: 'border-rose-500/20 bg-rose-500/5',
          text: 'OFFLINE',
          pulse: false,
          icon: WifiOff
        };
      default:
        return {
          dotColor: 'bg-slate-500',
          textColor: 'text-slate-400',
          borderColor: 'border-slate-500/20 bg-slate-500/5',
          text: 'UNKNOWN',
          pulse: false,
          icon: AlertTriangle
        };
    }
  };

  const config = getStatusConfig(status);
  const IconComponent = config.icon;

  return (
    <div className={`flex items-center justify-between px-3 py-1.5 border rounded-lg transition-all duration-300 ${config.borderColor}`}>
      <div className="flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          {config.pulse && (
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${config.dotColor}`} />
          )}
          <span className={`relative inline-flex rounded-full h-2 w-2 ${config.dotColor}`} />
        </span>
        <span className={`text-[11px] font-bold tracking-wider uppercase font-mono ${config.textColor}`}>
          {config.text}
        </span>
      </div>
      <span className="text-[10px] font-mono text-slate-400 tabular-nums">
        {lastEventTime}s ago
      </span>
    </div>
  );
};

export default SystemStatusBar;

