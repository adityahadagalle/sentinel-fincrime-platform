import React, { useState, useEffect, useRef } from 'react';
import { getRole } from '../roleStore';
import { maskAccount } from '../utils/maskAccount';
import { ShieldAlert, AlertTriangle } from 'lucide-react';

const LiveAlertToast = () => {
  const [activeAlert, setActiveAlert] = useState(null);
  const timerRef = useRef(null);
  const seenAlertsRef = useRef(new Map());
  const activeAlertRef = useRef(null);

  useEffect(() => {
    const handleAlert = (event) => {
      const data = event.detail || {};
      const score = Number(data.risk_score || 0);

      // Trigger threshold: HIGH (70-84) and CRITICAL (>=85)
      if (score < 70) return;

      const txId = data.tx_id || data.id;
      const now = Date.now();

      // Deduplicate: Don't show repeated alert for the same transaction within 10s
      if (txId) {
        const lastSeen = seenAlertsRef.current.get(txId);
        if (lastSeen && now - lastSeen < 10000) {
          return;
        }
        seenAlertsRef.current.set(txId, now);
        if (seenAlertsRef.current.size > 100) {
          for (const [k, v] of seenAlertsRef.current.entries()) {
            if (now - v > 30000) seenAlertsRef.current.delete(k);
          }
        }
      }

      // Check transaction age: ignore stale historical transactions older than 30s
      if (data.timestamp) {
        const age = now - new Date(data.timestamp).getTime();
        if (!isNaN(age) && age > 30000) {
          return;
        }
      }

      const role = getRole();
      const isViewer = role !== 'admin';
      const displaySender = isViewer ? maskAccount(data.sender_account) : data.sender_account;
      const amountFormatted = `₹${Number(data.amount || 0).toLocaleString()}`;

      const isCritical = score >= 85;
      const duration = isCritical ? 3200 : 2400; // Display duration in ms

      const newAlert = {
        id: txId || Math.random().toString(36).substr(2, 9),
        tx_id: txId,
        title: isCritical ? 'CRITICAL FRAUD DETECTED' : 'HIGH RISK TRANSACTION',
        message: `${amountFormatted} • ${displaySender}`,
        score,
        isCritical,
        duration
      };

      // Burst throttling:
      // If an alert is actively showing, prevent rapid visual strobe
      if (activeAlertRef.current) {
        const currentIsCritical = activeAlertRef.current.isCritical;
        const timeSinceActive = now - (activeAlertRef.current.displayedAt || 0);

        // Keep CRITICAL alert if incoming is only HIGH
        if (!isCritical && currentIsCritical) {
          return;
        }

        // Throttle same severity within 1.2s
        if (timeSinceActive < 1200 && (!isCritical || currentIsCritical)) {
          return;
        }
      }

      newAlert.displayedAt = now;
      activeAlertRef.current = newAlert;

      // Clear existing dismiss timer to avoid premature closing of replacement alert
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }

      // Replace active alert with newest to prevent vertical stacking/flooding
      setActiveAlert(newAlert);

      // Auto-dismiss timer
      timerRef.current = setTimeout(() => {
        setActiveAlert(null);
        activeAlertRef.current = null;
        timerRef.current = null;
      }, duration);
    };

    window.addEventListener('sentinel_alert', handleAlert);
    return () => {
      window.removeEventListener('sentinel_alert', handleAlert);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  if (!activeAlert) return null;

  return (
    <div className="fixed top-5 right-8 z-[100] pointer-events-none font-sans select-none animate-in fade-in slide-in-from-top-2 duration-200">
      <div
        className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl backdrop-blur-md shadow-2xl border pointer-events-none transition-all ${
          activeAlert.isCritical
            ? 'bg-slate-950/90 border-rose-500/50 text-rose-300 shadow-rose-950/50'
            : 'bg-slate-950/90 border-amber-500/50 text-amber-300 shadow-amber-950/50'
        }`}
      >
        <div
          className={`p-1.5 rounded-lg ${
            activeAlert.isCritical ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-400'
          }`}
        >
          {activeAlert.isCritical ? (
            <ShieldAlert className="w-4 h-4 shrink-0 animate-pulse" />
          ) : (
            <AlertTriangle className="w-4 h-4 shrink-0" />
          )}
        </div>

        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-bold tracking-wider uppercase">
              {activeAlert.title}
            </span>
            <span
              className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-bold ${
                activeAlert.isCritical ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300'
              }`}
            >
              SCORE {activeAlert.score}
            </span>
          </div>
          <span className="text-xs font-mono font-medium text-slate-200 truncate mt-0.5">
            {activeAlert.message}
          </span>
        </div>
      </div>
    </div>
  );
};

export default LiveAlertToast;


