import React, { useState, useMemo } from 'react';
import { twMerge } from 'tailwind-merge';

/**
 * React Bits Pro Center Flow Component
 * 
 * Supports official React Bits Center Flow contract:
 * - `nodeItems`: Array of surrounding peripheral node items with custom content
 * - `centerContent`: Custom ReactNode for the central hub
 * - `centerSize`: Diameter of center hub in pixels
 * - `nodeSize`: Diameter of peripheral nodes in pixels
 * - `nodeDistance`: Distance multiplier from center (0.0 to 1.0)
 * - `lineWidth`, `lineColor`: Conduit line styling
 * - `pulseWidth`, `pulseDuration`, `pulseInterval`, `pulseLength`, `pulseSoftness`: Radial pulse animation
 * - `maxGlowIntensity`, `glowDecay`, `disableBlinking`: Glow and lighting controls
 * - `className`: Custom wrapper styling
 */
export const CenterFlow = ({
  nodeItems = [],
  centerContent = null,
  centerSize = 120,
  nodeSize = 56,
  nodeDistance = 0.72,
  lineWidth = 1.5,
  lineColor = '#06b6d4',
  pulseWidth = 2.5,
  pulseDuration = 3,
  pulseInterval = 1.5,
  pulseLength = 28,
  pulseSoftness = 3,
  maxGlowIntensity = 0.8,
  glowDecay = 0.4,
  disableBlinking = false,
  className = '',
  onNodeClick = () => {},
  onNodeHover = () => {},
  selectedNodeId = null
}) => {
  const [internalHoveredId, setInternalHoveredId] = useState(null);

  const totalNodes = nodeItems.length;

  // Compute radial positions for all nodes in a clockwise circular distribution
  // Starting from top (-90 degrees)
  const nodePositions = useMemo(() => {
    if (totalNodes === 0) return [];
    
    // Total container radius normalized to 50%
    // nodeDistance scales the radius from center
    const radiusPercent = Math.min(Math.max(nodeDistance * 44, 25), 45);

    return nodeItems.map((item, index) => {
      // Angle in radians: theta_0 = -PI/2 (top), then clockwise
      const angle = -Math.PI / 2 + (index * 2 * Math.PI) / totalNodes;
      const xPercent = 50 + radiusPercent * Math.cos(angle);
      const yPercent = 50 + radiusPercent * Math.sin(angle);

      return {
        item,
        index,
        angle,
        xPercent,
        yPercent
      };
    });
  }, [nodeItems, totalNodes, nodeDistance]);

  return (
    <div 
      className={twMerge(
        "relative w-full overflow-hidden select-none flex items-center justify-center",
        className
      )}
      style={{ minHeight: `${centerSize * 2.8}px` }}
    >
      {/* ── SVG CONDUIT & PULSE LAYER ─────────────────────────────────────── */}
      <svg 
        className="absolute inset-0 w-full h-full pointer-events-none overflow-visible z-0"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        <defs>
          {/* Radial Center Glow Gradient */}
          <radialGradient id="center-hub-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity={maxGlowIntensity * 0.3} />
            <stop offset="70%" stopColor="#0B132B" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#060B15" stopOpacity="0" />
          </radialGradient>

          {/* Glowing Filters */}
          <filter id="conduit-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation={pulseSoftness * 0.4} result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          {/* Flow Chevrons */}
          <marker id="cf-arrow-emerald" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
            <path d="M0,0 L5,2.5 L0,5 Z" fill="#10B981" />
          </marker>
          <marker id="cf-arrow-sky" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
            <path d="M0,0 L5,2.5 L0,5 Z" fill="#38BDF8" />
          </marker>
          <marker id="cf-arrow-slate" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
            <path d="M0,0 L5,2.5 L0,5 Z" fill="#475569" />
          </marker>
        </defs>

        {/* Ambient Center Glow */}
        <circle cx="50" cy="50" r="30" fill="url(#center-hub-glow)" />

        {/* Outer Sequential Conduits (01 -> 02 -> 03 -> 04 -> 05) */}
        {nodePositions.map((pos, idx) => {
          if (idx >= totalNodes - 1) return null;
          const nextPos = nodePositions[idx + 1];
          const isComp = pos.item.status === 'COMPLETED';
          const isNextComp = nextPos.item.status === 'COMPLETED';
          const isNextRun = nextPos.item.status === 'RUNNING';

          const stroke = isComp && isNextComp ? '#10B981' :
                         isComp && isNextRun ? '#38BDF8' :
                         '#334155';
          const marker = isComp && isNextComp ? 'url(#cf-arrow-emerald)' :
                         isComp && isNextRun ? 'url(#cf-arrow-sky)' :
                         'url(#cf-arrow-slate)';

          return (
            <line
              key={`seq-${idx}`}
              x1={pos.xPercent}
              y1={pos.yPercent}
              x2={nextPos.xPercent}
              y2={nextPos.yPercent}
              stroke={stroke}
              strokeWidth={lineWidth * 0.8}
              strokeDasharray={isComp && isNextRun ? "3,2" : "none"}
              markerEnd={marker}
              opacity={0.7}
            />
          );
        })}

        {/* Radial Conduits from Center Hub to each Peripheral Node */}
        {nodePositions.map((pos, idx) => {
          const isSelected = selectedNodeId === pos.item.id;
          const isHovered = internalHoveredId === pos.item.id;
          const isComplete = pos.item.status === 'COMPLETED';
          const isRunning = pos.item.status === 'RUNNING';

          const stroke = isSelected || isHovered ? '#38BDF8' :
                         isComplete ? '#10B981' :
                         isRunning ? '#38BDF8' :
                         lineColor || '#334155';

          return (
            <g key={`radial-${idx}`}>
              {/* Static Base Conduit */}
              <line
                x1="50"
                y1="50"
                x2={pos.xPercent}
                y2={pos.yPercent}
                stroke={stroke}
                strokeWidth={isHovered || isSelected ? lineWidth * 1.6 : lineWidth}
                strokeOpacity={isHovered || isSelected ? 0.9 : 0.4}
                filter={isHovered || isSelected ? "url(#conduit-glow)" : "none"}
                className="transition-all duration-300"
              />

              {/* Dynamic Animated Pulse Along Radial Conduit */}
              {!disableBlinking && (isComplete || isRunning || isHovered) && (
                <line
                  x1="50"
                  y1="50"
                  x2={pos.xPercent}
                  y2={pos.yPercent}
                  stroke={isRunning || isHovered ? '#38BDF8' : '#10B981'}
                  strokeWidth={pulseWidth}
                  strokeLinecap="round"
                  strokeDasharray={`${pulseLength}, 100`}
                  strokeDashoffset="0"
                  opacity={0.85}
                  filter="url(#conduit-glow)"
                >
                  <animate
                    attributeName="stroke-dashoffset"
                    from="100"
                    to="0"
                    dur={`${pulseDuration}s`}
                    begin={`${idx * (pulseDuration / totalNodes)}s`}
                    repeatCount="indefinite"
                  />
                </line>
              )}
            </g>
          );
        })}
      </svg>

      {/* ── CENTRAL ORCHESTRATOR HUB ─────────────────────────────────────── */}
      <div 
        className="relative z-10 flex items-center justify-center"
        style={{ width: `${centerSize}px`, height: `${centerSize}px` }}
      >
        <div className="w-full h-full rounded-full bg-[#081020]/95 backdrop-blur-md border-2 border-sky-500/50 flex flex-col items-center justify-center p-3 shadow-[0_0_28px_rgba(6,182,212,0.3)] text-center transition-all duration-300 relative group">
          {/* Subtle Outer Halo Pulse */}
          <div className="absolute inset-0 rounded-full border border-sky-400/40 animate-ping opacity-30 pointer-events-none" />
          
          {centerContent ? (
            centerContent
          ) : (
            <div className="space-y-1">
              <div className="text-[10px] font-mono font-bold tracking-wider text-sky-400 uppercase">
                ORCHESTRATOR
              </div>
              <div className="text-[9px] font-mono text-slate-400">
                PIPELINE HUB
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── PERIPHERAL STAGE NODES ────────────────────────────────────────── */}
      {nodePositions.map((pos) => {
        const { item, xPercent, yPercent } = pos;
        const isSelected = selectedNodeId === item.id;
        const isHovered = internalHoveredId === item.id;
        const isComplete = item.status === 'COMPLETED';
        const isRunning = item.status === 'RUNNING';
        const isFailed = item.status === 'FAILED';

        return (
          <div
            key={item.id}
            style={{ 
              left: `${xPercent}%`, 
              top: `${yPercent}%`,
              width: `${nodeSize}px`,
              height: `${nodeSize}px`
            }}
            className="absolute -translate-x-1/2 -translate-y-1/2 z-20"
            onMouseEnter={() => {
              setInternalHoveredId(item.id);
              onNodeHover(item);
            }}
            onMouseLeave={() => {
              setInternalHoveredId(null);
              onNodeHover(null);
            }}
            onClick={() => onNodeClick(item)}
          >
            {/* Interactive Node Element */}
            <div 
              className={twMerge(
                "w-full h-full rounded-full flex flex-col items-center justify-center cursor-pointer transition-all duration-200 relative select-none",
                isSelected
                  ? "bg-[#0E1A38] border-2 border-sky-400 text-sky-300 ring-4 ring-sky-400/50 shadow-[0_0_24px_rgba(6,182,212,0.5)] scale-115 z-30"
                  : isHovered
                  ? "bg-[#0E1A38] border-2 border-sky-400 text-sky-300 scale-110 shadow-[0_0_18px_rgba(6,182,212,0.4)] z-30"
                  : isComplete
                  ? "bg-[#061A18]/95 border-2 border-emerald-500/80 text-emerald-400 hover:border-emerald-400 hover:shadow-[0_0_15px_rgba(16,185,129,0.35)]"
                  : isRunning
                  ? "bg-sky-500/20 border-2 border-sky-400 text-sky-300 ring-2 ring-sky-400/40 animate-pulse"
                  : isFailed
                  ? "bg-rose-500/20 border-2 border-rose-500 text-rose-400"
                  : "bg-[#0B132B]/90 border border-slate-700 text-slate-500 hover:border-slate-500"
              )}
              title={`${item.fullName || item.title} (${item.status})`}
            >
              {item.content || (
                <div className="flex flex-col items-center justify-center p-1">
                  {item.icon && <item.icon className="w-4 h-4" />}
                  <span className="text-[9px] font-mono font-bold uppercase mt-0.5 tracking-wider truncate max-w-[46px]">
                    {item.label || item.title}
                  </span>
                </div>
              )}

              {/* Status Indicator Tick on Edge */}
              <span className={twMerge(
                "absolute -top-1 -right-1 w-4 h-4 rounded-full border border-[#0B132B] flex items-center justify-center font-mono text-[8px] font-bold shadow-sm",
                isComplete ? "bg-emerald-500 text-black" :
                isRunning ? "bg-sky-400 text-black animate-pulse" :
                isFailed ? "bg-rose-500 text-white" :
                "bg-slate-700 text-slate-400"
              )}>
                {isComplete ? '✓' : isRunning ? '●' : isFailed ? '!' : item.index || '○'}
              </span>
            </div>

            {/* Label below node for clear accessibility */}
            <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 text-center pointer-events-none whitespace-nowrap">
              <span className={twMerge(
                "text-[9px] font-mono font-bold tracking-wider uppercase block",
                isSelected || isHovered ? "text-sky-300" : "text-slate-300"
              )}>
                {item.title}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default CenterFlow;
