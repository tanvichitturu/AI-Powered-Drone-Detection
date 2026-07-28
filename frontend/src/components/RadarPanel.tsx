import { useMemo } from 'react';
import type { Alert } from '@/types';
import { THREAT_COLORS } from '@/types';

const SIZE = 500;
const CENTER = SIZE / 2;
const SCALE_FACTOR = 1.5; 

export default function RadarPanel({ alerts }: { alerts: Alert[] }) {
  const blips = useMemo(
    () =>
      alerts.map((a) => {
        const [x, y] = a.current_position;
        const normalizedX = (x - 320) / SCALE_FACTOR; 
        const normalizedY = (y - 240) / SCALE_FACTOR;

        return { 
          ...a, 
          cx: CENTER + normalizedX, 
          cy: CENTER - normalizedY, 
          color: THREAT_COLORS[a.threat_level]?.dot || '#ef4444' 
        };
      }),
      [alerts],
  );

  return (
    <div className="glass rounded-xl p-4">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <h3 className="display flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-200">
          <span className="h-2 w-2 animate-blink rounded-full bg-accent-400" /> Tactical Vision (2D Radar)
        </h3>
      </div>

      {/* Main Display Area - Radar Only */}
      <div className="flex justify-center items-center min-h-[500px]">
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} className="max-w-full">
          <defs>
            <radialGradient id="rg" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#0ea5e9" stopOpacity="0.18" />
              <stop offset="70%" stopColor="#0ea5e9" stopOpacity="0.03" />
              <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0" />
            </radialGradient>
          </defs>

          <circle cx={CENTER} cy={CENTER} r={240} fill="url(#rg)" />
          {[80, 160, 240].map((r) => (
            <circle key={r} cx={CENTER} cy={CENTER} r={r} fill="none" stroke="#1e3a5f" strokeWidth="1" />
          ))}
          <line x1={CENTER} y1={20} x2={CENTER} y2={SIZE - 20} stroke="#1e3a5f" strokeWidth="1" />
          <line x1={20} y1={CENTER} x2={SIZE - 20} y2={CENTER} stroke="#1e3a5f" strokeWidth="1" />

          <circle cx={CENTER} cy={CENTER} r={160} fill="none" stroke="#eab308" strokeWidth="1.5" strokeDasharray="6 6" opacity="0.7" />
          <circle cx={CENTER} cy={CENTER} r={80} fill="rgba(239,68,68,0.06)" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="5 5" opacity="0.8" />

          <g style={{ transformOrigin: 'center' }} className="animate-radar-sweep">
            <line x1={CENTER} y1={CENTER} x2={CENTER} y2={20} stroke="#0ea5e9" strokeOpacity="0.8" strokeWidth="2" />
            <path d={`M ${CENTER} ${CENTER} L ${CENTER} 20 A 240 240 0 0 1 ${CENTER + 70} ${CENTER - 230} Z`} fill="#0ea5e9" fillOpacity="0.1" />
          </g>

          <circle cx={CENTER} cy={CENTER} r="4" fill="#0ea5e9" />
          <circle cx={CENTER} cy={CENTER} r="8" fill="none" stroke="#0ea5e9" strokeOpacity="0.5" />

          {blips.map((b) => (
            <g key={b.drone_id}>
              <circle cx={b.cx} cy={b.cy} r="10" fill={b.color} opacity="0.18" className="animate-drone-pulse" />
              <circle cx={b.cx} cy={b.cy} r="4" fill={b.color} />
              <text x={b.cx + 8} y={b.cy - 6} fontSize="11" fontFamily="Orbitron, sans-serif" fill={b.color} className="font-medium">#{b.drone_id}</text>
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}