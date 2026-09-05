import React, { useState, useEffect, useRef } from 'react';
import { ShieldAlert, AlertTriangle, Activity, Lock, CheckCircle2, XCircle, Zap, Bot, MinusCircle } from 'lucide-react';
import { usePresentationMode } from '../hooks/usePresentationMode';
import { getPresentationMode } from '../presentationStore';
import { useLocation } from 'react-router-dom';

const ActionTakenToast = () => {
  const location = useLocation();
  const isMLPage = location.pathname === '/ml-intelligence' || location.pathname.startsWith('/ml-intelligence');
  const { isPresentationMode } = usePresentationMode();
  const [activeAction, setActiveAction] = useState(null);
  const timerRef = useRef(null);
  const seenActionsRef = useRef(new Map());

  // Clear active action toast immediately if Presentation Mode or ML page is activated
  useEffect(() => {
    if (isPresentationMode || isMLPage) {
      setActiveAction(null);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    }
  }, [isPresentationMode, isMLPage]);

  useEffect(() => {
    const handleAction = (event) => {
      // Suppress action toast popups if Presentation Mode is active or on ML page
      if (isMLPage || getPresentationMode()) return;

      const data = event.detail || {};
      const rec = data.execution_record || data.execution_result || data;
      const pol = data.policy_decision || {};

      const score = Number(data.risk_score || rec.risk_score || pol.risk_score || 0);
      const risk_level = data.risk_level || rec.risk_level || pol.risk_level || (score >= 85 ? 'CRITICAL' : score >= 70 ? 'HIGH' : score >= 40 ? 'MEDIUM' : 'LOW');
      const isCritical = score >= 85 || risk_level === 'CRITICAL';
      
      const execStatus = data.execution_status || data.action_status || rec.execution_status || rec.action_status || 'NOT_EXECUTED';
      const mode = rec.automation_mode || rec.mode || data.mode || (pol.automation_enabled ? 'AUTOMATE_ON' : 'AUTOMATE_OFF');
      const rawAction = (data.action || data.action_code || rec.action_code || rec.action || pol.action || '').toUpperCase();
      const isFreeze = rawAction === 'FREEZE';
      const actorType = data.actor_type || rec.actor_type || (isFreeze ? 'HUMAN_OPERATOR' : 'AUTOMATION_ENGINE');
      const isHumanOperator = actorType === 'HUMAN_OPERATOR';
      
      const isFailedFreeze = event.type === 'sentinel_freeze_failed' || data.is_failed_freeze;
      const isOperatorReq = !isFailedFreeze && (execStatus === 'REQUIRES_OPERATOR_ACTION' || (isFreeze && !isHumanOperator));
      const isBlocked = !isFailedFreeze && (execStatus === 'REJECTED' || pol.decision === 'REJECT');
      const isFailed = isFailedFreeze || execStatus === 'FAILED';
      const isExecuted = !isFailedFreeze && (execStatus === 'SUCCESS' || execStatus === 'EXECUTED') && !isFreeze;
      const isOperatorFreezeExecuted = !isFailedFreeze && isFreeze && isHumanOperator && (execStatus === 'SUCCESS' || execStatus === 'EXECUTED');

      // Requirement: Do NOT show a temporary success toast for FREEZE. The workstation state is the confirmation.
      if (isOperatorFreezeExecuted) {
        return;
      }

      // Routine MONITOR is baseline telemetry, NOT an enforcement popup event
      if (rawAction === 'MONITOR' || rawAction === '') {
        return;
      }

      // Suppress toast if no meaningful action lifecycle event occurred
      if (!isOperatorReq && !isFailed && !isBlocked && !isExecuted) {
        return;
      }

      const txId = data.transaction_id || data.tx_id || rec.transaction_id || 'UNKNOWN';
      const now = Date.now();
      const dedupeKey = `${txId}_${rawAction}_${execStatus}`;

      // Deduplicate: suppress repeated duplicate action toasts within 5s
      if (txId !== 'UNKNOWN') {
        const lastSeen = seenActionsRef.current.get(dedupeKey);
        if (lastSeen && now - lastSeen < 5000) {
          return;
        }
        seenActionsRef.current.set(dedupeKey, now);
        if (seenActionsRef.current.size > 100) {
          for (const [k, v] of seenActionsRef.current.entries()) {
            if (now - v > 30000) seenActionsRef.current.delete(k);
          }
        }
      }

      let title = isHumanOperator ? '⚡ OPERATOR ACTION EXECUTED' : '⚡ AUTOMATED ACTION EXECUTED';
      if (isOperatorReq) {
        title = '🔔 OPERATOR ACTION REQUIRED';
      } else if (isFailedFreeze || isFailed) {
        title = '⚠ FREEZE FAILED';
      } else if (isBlocked) {
        title = '🔒 ACTION BLOCKED BY POLICY';
      }

      const duration = (isFailedFreeze || isFailed) ? 4000 : 2500;

      const newAction = {
        id: dedupeKey,
        tx_id: txId,
        account_id: data.account_id || data.sender_account || rec.account_id || 'ACC-XXXX',
        score,
        risk_level,
        action: isFreeze ? 'FREEZE ACCOUNT' : rawAction.replace(/_/g, ' '),
        action_status: isOperatorFreezeExecuted ? 'SUCCESS' : isFailedFreeze ? 'NOT FROZEN' : isOperatorReq ? 'Awaiting operator approval' : execStatus,
        mode,
        actor_type: isOperatorFreezeExecuted ? 'HUMAN OPERATOR' : isOperatorReq ? 'HUMAN OPERATOR' : 'AUTOMATION ENGINE',
        policy_rule_id: pol.policy_rule_id || rec.policy_rule_id || 'POL-DEFAULT',
        reason: data.error || pol.reason || data.reason || rec.reason || 'Deterministic policy engine evaluation.',
        title,
        isOperatorReq,
        isOperatorFreezeExecuted,
        isBlocked,
        isFailed: isFailedFreeze || isFailed,
        isExecuted,
        duration
      };

      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }

      setActiveAction(newAction);

      timerRef.current = setTimeout(() => {
        setActiveAction(null);
        timerRef.current = null;
      }, duration);
    };

    window.addEventListener('sentinel_transaction_action', handleAction);
    window.addEventListener('sentinel_automation_action', handleAction);
    window.addEventListener('sentinel_freeze_failed', handleAction);
    return () => {
      window.removeEventListener('sentinel_transaction_action', handleAction);
      window.removeEventListener('sentinel_automation_action', handleAction);
      window.removeEventListener('sentinel_freeze_failed', handleAction);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isMLPage]);

  if (isPresentationMode || isMLPage || !activeAction) return null;

  return (
    <div className="fixed bottom-6 right-8 z-[110] font-sans select-none animate-in fade-in slide-in-from-bottom-3 duration-200 max-w-md w-full">
      <div
        className={`p-4 rounded-xl backdrop-blur-xl shadow-2xl border transition-all ${
          activeAction.isOperatorFreezeExecuted
            ? 'bg-rose-950/95 border-rose-500/90 text-rose-200 shadow-rose-950/80'
            : activeAction.isOperatorReq
            ? 'bg-amber-950/95 border-amber-500/90 text-amber-200 shadow-amber-950/80 animate-pulse'
            : activeAction.isFailed
            ? 'bg-rose-950/95 border-rose-500/80 text-rose-200 shadow-rose-950/60'
            : 'bg-slate-950/95 border-emerald-500/60 text-emerald-300 shadow-emerald-950/40'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-white/10">
          <div className="flex items-center gap-2">
            <div
              className={`p-1.5 rounded-lg ${
                activeAction.isOperatorFreezeExecuted
                  ? 'bg-rose-500/25 text-rose-300'
                  : activeAction.isOperatorReq
                  ? 'bg-amber-500/25 text-amber-300'
                  : activeAction.isFailed
                  ? 'bg-rose-500/20 text-rose-400'
                  : 'bg-emerald-500/20 text-emerald-400'
              }`}
            >
              {activeAction.isOperatorFreezeExecuted ? (
                <Lock className="w-4 h-4 text-rose-300" />
              ) : activeAction.isOperatorReq ? (
                <AlertTriangle className="w-4 h-4 text-amber-300 animate-pulse" />
              ) : activeAction.isFailed ? (
                <XCircle className="w-4 h-4 text-rose-400" />
              ) : (
                <Zap className="w-4 h-4 text-emerald-400 animate-pulse" />
              )}
            </div>
            <span className="text-xs font-mono font-bold tracking-wider uppercase text-slate-100 flex items-center gap-1.5">
              {activeAction.title}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold bg-slate-800 text-slate-300 border border-slate-700">
              {activeAction.tx_id}
            </span>
            <span
              className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold ${
                activeAction.risk_level === 'CRITICAL'
                  ? 'bg-rose-500/25 text-rose-300 border border-rose-500/40'
                  : 'bg-emerald-500/25 text-emerald-300 border border-emerald-500/40'
              }`}
            >
              SCORE {activeAction.score} ({activeAction.risk_level})
            </span>
          </div>
        </div>

        {/* Content Details */}
        <div className="space-y-2 text-xs">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
              {activeAction.isOperatorReq ? 'RECOMMENDED ACTION' : 'ACTION'}
            </div>
            <div className="font-mono font-bold text-slate-100 uppercase tracking-wide">
              {activeAction.action}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">EXECUTED BY</div>
              <div className="font-mono font-semibold text-slate-200 uppercase">
                {activeAction.actor_type}
              </div>
            </div>

            <div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">STATUS</div>
              <div className="font-mono font-semibold text-slate-200 uppercase flex items-center gap-1">
                {activeAction.isOperatorFreezeExecuted ? (
                  <Lock className="w-3 h-3 text-rose-400" />
                ) : activeAction.isOperatorReq ? (
                  <AlertTriangle className="w-3 h-3 text-amber-400" />
                ) : activeAction.isExecuted ? (
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                ) : (
                  <Activity className="w-3 h-3 text-slate-400" />
                )}
                {activeAction.action_status}
              </div>
            </div>
          </div>

          {activeAction.isOperatorReq && (
            <div className="p-2 bg-amber-900/40 border border-amber-500/30 rounded-lg text-[11px] font-mono text-amber-200">
              Operator Approval Required. Click FREEZE control on transaction feed to execute.
            </div>
          )}

          <div className="pt-1.5 border-t border-white/5">
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">REASON</div>
            <div className="text-[11px] font-sans text-slate-300 leading-snug line-clamp-2 mt-0.5">
              {activeAction.reason}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};



export default ActionTakenToast;
