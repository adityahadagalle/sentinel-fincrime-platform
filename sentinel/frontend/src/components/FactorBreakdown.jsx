import React from 'react';

const FactorBreakdown = ({ factors = [] }) => {
  // Sort factors by contribution (descending)
  const sortedFactors = [...factors].sort((a, b) => b.contribution - a.contribution);

  return (
    <div className="space-y-3 font-sans">
      <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Risk Factor Breakdown</h3>
      <div className="space-y-2">
        {sortedFactors.length > 0 ? (
          sortedFactors.map((factor, index) => (
            <div 
              key={`${factor.name}-${index}`}
              className="group bg-slate-900/60 hover:bg-slate-900 p-2.5 rounded-lg border border-border/60 transition-all"
            >
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs font-semibold text-sky-400">
                  {factor.name.replace(/_/g, ' ')}
                </span>
                <span className="text-xs font-mono font-bold text-rose-400">
                  +{factor.contribution}%
                </span>
              </div>
              <div className="flex justify-between items-center text-[10px] text-slate-400 mb-1.5 font-mono">
                <span>Weight: {factor.weight}</span>
                <span>
                  {typeof factor.value === 'number' ? `₹${factor.value.toLocaleString()}` : factor.value}
                </span>
              </div>
              {/* Progress bar */}
              <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-rose-500 transition-all duration-300"
                  style={{ width: `${Math.min(factor.contribution, 100)}%` }}
                />
              </div>
            </div>
          ))
        ) : (
          <p className="text-xs text-slate-400 italic">No risk factors identified.</p>
        )}
      </div>
    </div>
  );
};

export default FactorBreakdown;

