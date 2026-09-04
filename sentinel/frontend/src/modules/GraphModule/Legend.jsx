import React from 'react';

const Legend = () => {
  const entityItems = [
    { label: 'Source', symbol: '●', color: '#2563EB' },
    { label: 'Mule', symbol: '⬢', color: '#DC2626' },
    { label: 'Collector', symbol: '▣', color: '#D97706' },
    { label: 'UPI', symbol: '◇', color: '#D97706' },
    { label: 'Crypto', symbol: '⬡', color: '#7C3AED' },
    { label: 'Merchant', symbol: '⌂', color: '#7C3AED' },
    { label: 'Cashout', symbol: '⌬', color: '#DC2626' }
  ];

  const flowItems = [
    { label: 'Standard Transfer', style: '—', color: '#38BDF8' },
    { label: 'Suspicious Flow', style: '- -', color: '#EF4444' },
    { label: 'Traced Route', style: '━━', color: '#38BDF8' }
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 p-3 rounded-xl shadow-2xl backdrop-blur-md font-mono text-[11px] text-slate-300 w-52 space-y-2.5">
      <div>
        <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 border-b border-slate-800/80 pb-1">ENTITY TYPES</h4>
        <div className="grid grid-cols-2 gap-x-2 gap-y-1">
          {entityItems.map((item) => (
            <div key={item.label} className="flex items-center gap-1.5">
              <span style={{ color: item.color }} className="font-bold text-xs">{item.symbol}</span>
              <span className="text-slate-300 text-[10px]">{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 border-b border-slate-800/80 pb-1">FLOW TYPES</h4>
        <div className="space-y-1">
          {flowItems.map((item) => (
            <div key={item.label} className="flex items-center justify-between">
              <span className="text-slate-400 text-[10px]">{item.label}</span>
              <span style={{ color: item.color }} className="font-bold text-[10px] font-mono">{item.style}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Legend;
