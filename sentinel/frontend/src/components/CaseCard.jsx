import React, { useState } from 'react';
import RiskBadge from './RiskBadge';
import GoldenTimer from './GoldenTimer';
import ActionButton from './ActionButton';
import FactorBreakdown from './FactorBreakdown';
import { maskAccount } from '../utils/maskAccount';
import { Shield, ChevronDown, ChevronUp, AlertCircle, ArrowRight } from 'lucide-react';

const CaseCard = ({ caseData, onAnalyze, transactions = [], role }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const isViewer = role !== 'admin';
  
  if (!caseData) return null;

  const totalFraud = caseData.total_fraud_amount || 0;
  const recoverable = caseData.recoverable_amount || 0;
  const recoveryPercent = totalFraud > 0 ? ((recoverable / totalFraud) * 100).toFixed(1) : "0.0";

  // Get factors from the first transaction associated with this case
  const relatedTx = transactions.find(tx => tx.case_id === caseData.case_id);
  const factors = relatedTx?.risk_factors || [];

  const handleAction = async (e, actionEndpoint) => {
    e.stopPropagation();
    if (isViewer) return;
    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      await fetch(`${API_BASE}/action/${actionEndpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_id: caseData.case_id,
          account_id: 'GLOBAL',
          reason: `Action ${actionEndpoint} executed from Case Card`
        })
      });
    } catch (error) {
      console.error('Network error during action:', error);
    }
  };

  return (
    <div 
      onClick={() => onAnalyze && onAnalyze(caseData, relatedTx)}
      className={`bg-card border border-border/80 rounded-2xl p-5 shadow-xl transition-all duration-200 cursor-pointer flex flex-col justify-between ${
        isExpanded ? 'ring-1 ring-sky-500/50 border-sky-500/40' : 'hover:border-slate-700/80 hover:bg-slate-900/60'
      }`}
    >
      <div>
        {/* Card Header */}
        <div className="flex justify-between items-start mb-4">
          <div>
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">Case Identifier</span>
            <h3 className="text-base font-mono font-bold text-slate-100">{caseData.case_id}</h3>
          </div>
          <RiskBadge score={caseData.risk_level} />
        </div>

        {/* Chain & Recovery Status */}
        <div className="grid grid-cols-2 gap-3 p-3 bg-muted/30 rounded-xl border border-border/60 mb-4">
          <div>
            <span className="text-[10px] text-slate-400 block font-medium">Chain Depth</span>
            <span className="font-mono text-xs font-semibold text-slate-200">{caseData.chain?.length || 0} Accounts</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 block font-medium">Recovery Status</span>
            <span className="font-mono text-xs font-semibold text-emerald-400">{recoveryPercent}%</span>
          </div>
        </div>

        {/* Financial Metrics */}
        <div className="space-y-2 mb-4 px-1">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 font-medium">Total Fraud Value</span>
            <span className="font-mono font-semibold text-slate-100">₹{caseData.total_fraud_amount.toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400 font-medium">Recoverable Value</span>
            <span className="font-mono font-semibold text-emerald-400">₹{caseData.recoverable_amount.toLocaleString()}</span>
          </div>
        </div>

        {/* Status & Golden Timer */}
        <div className="pt-3 border-t border-border/60 flex justify-between items-center mb-4">
          <GoldenTimer minutes={caseData.golden_window_minutes} />
          <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/60 uppercase">
            {caseData.status}
          </span>
        </div>

        {/* Quick Action Buttons */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          <button 
            onClick={(e) => handleAction(e, 'freeze')} 
            disabled={isViewer} 
            className="py-1.5 px-2 bg-rose-600/90 hover:bg-rose-600 text-white rounded-lg text-[10px] font-semibold transition-colors disabled:opacity-40"
          >
            Freeze
          </button>
          <button 
            onClick={(e) => handleAction(e, 'alert')} 
            disabled={isViewer} 
            className="py-1.5 px-2 bg-sky-600/90 hover:bg-sky-600 text-white rounded-lg text-[10px] font-semibold transition-colors disabled:opacity-40"
          >
            Police
          </button>
          <button 
            onClick={(e) => handleAction(e, 'flag')} 
            disabled={isViewer} 
            className="py-1.5 px-2 bg-amber-600/90 hover:bg-amber-600 text-white rounded-lg text-[10px] font-semibold transition-colors disabled:opacity-40"
          >
            Escalate
          </button>
        </div>
      </div>

      {/* Expandable Chain Section */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-border/60 space-y-4 animate-in fade-in duration-200">
          <div>
            <h4 className="text-[10px] font-semibold uppercase text-slate-400 mb-2 tracking-wider">Transaction Chain</h4>
            <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono bg-slate-900/80 p-2.5 rounded-lg border border-border/60">
              {caseData.chain.map((account, idx) => (
                <React.Fragment key={account}>
                  <span className="bg-sky-500/10 text-sky-400 px-1.5 py-0.5 rounded border border-sky-500/20">
                    {isViewer ? maskAccount(account) : account}
                  </span>
                  {idx < caseData.chain.length - 1 && <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />}
                </React.Fragment>
              ))}
            </div>
          </div>
          <FactorBreakdown factors={factors} />
        </div>
      )}

      <button 
        onClick={(e) => { e.stopPropagation(); setIsExpanded(!isExpanded); }}
        className="w-full flex items-center justify-center gap-1 text-[11px] font-medium text-slate-400 hover:text-sky-400 transition-colors pt-2 border-t border-border/40 mt-1"
      >
        <span>{isExpanded ? 'Collapse Details' : 'View Chain Details'}</span>
        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>
    </div>
  );
};

export default CaseCard;

