import React from 'react';

/**
 * Entity Geometries Legend Component
 * Standardized across SENTINEL design system.
 */
const Legend = () => {
  const entityTypes = [
    { label: 'Victim Account', color: '#0A1A3C', border: '#2563EB', shape: 'rounded-full' },
    { label: 'Mule Account', color: '#330808', border: '#DC2626', shape: 'rounded-sm' },
    { label: 'Merchant Outlet', color: '#03261A', border: '#10B981', shape: 'rounded-sm' },
    { label: 'UPI Handle', color: '#220B3D', border: '#9333EA', shape: 'rotate-45' },
    { label: 'Cashout Terminal', color: '#331B03', border: '#F59E0B', shape: 'rounded-sm' }
  ];

  const lineTypes = [
    { label: 'Suspicious Flow', color: '#EF4444', dashed: true },
    { label: 'Standard Transfer', color: '#2563EB', dashed: false },
    { label: 'Traced Active Route', color: '#38BDF8', dashed: false }
  ];

  return (
    <div className="p-3 bg-[#060B14]/95 border border-[#1E2D4A] rounded-lg shadow-2xl backdrop-blur-md space-y-2.5 font-['JetBrains_Mono'] text-[10px] select-none max-w-[210px]">
      <div>
        <span className="text-[8.5px] font-bold uppercase tracking-[0.14em] text-slate-500 block mb-1.5 border-b border-[#1E2D4A] pb-1">
          Entity Geometries
        </span>
        <div className="space-y-1.5">
          {entityTypes.map((item) => (
            <div key={item.label} className="flex items-center gap-2">
              <div
                className={`w-3 h-3 ${item.shape} shrink-0 border`}
                style={{ background: item.color, borderColor: item.border }}
              />
              <span className="text-[9.5px] text-slate-300 truncate">
                {item.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="pt-2 border-t border-[#1E2D4A]">
        <span className="text-[8.5px] font-bold uppercase tracking-[0.14em] text-slate-500 block mb-1.5 border-b border-[#1E2D4A] pb-1">
          Flow Paths
        </span>
        <div className="space-y-1.5">
          {lineTypes.map((line) => (
            <div key={line.label} className="flex items-center gap-2">
              <div
                className={`w-4 h-0.5 shrink-0 ${line.dashed ? 'border-b border-dashed border-red-500' : ''}`}
                style={{ background: line.dashed ? 'transparent' : line.color }}
              />
              <span className="text-[9.5px] text-slate-300 truncate">
                {line.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Legend;
