import { RefreshCw, Plane, Activity } from 'lucide-react';
import type { StatusResponse } from '@/types';
import { THREAT_COLORS } from '@/types';

interface ThreatStatusProps {
  status: StatusResponse;
  lastUpdated: number;
  connected: boolean;
  refreshing: boolean;
  onRefresh: () => void;
}

export default function ThreatStatus({
  status,
  lastUpdated,
  connected,
  refreshing,
  onRefresh,
}: ThreatStatusProps) {
  const c = THREAT_COLORS[status.threat_level];

  return (
    <div className="glass rounded-xl p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="display flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-200">
          <Activity size={16} className="text-accent-400" /> Threat Status
        </h3>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="btn-ghost !px-3 !py-1.5 text-xs"
        >
          <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
          {refreshing ? 'Refreshing' : 'Refresh Now'}
        </button>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <span className={`inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-bold uppercase tracking-wider ${c.bg} ${c.border} ${c.text}`}>
          <span className="h-2 w-2 animate-blink rounded-full" style={{ backgroundColor: c.dot }} />
          {c.label}
        </span>
        <span className="text-xs text-slate-500">
          updated {new Date(lastUpdated).toLocaleTimeString()}
        </span>
      </div>

      <div>
        <p className="mb-2 text-xs uppercase tracking-wider text-slate-500">Active Drone IDs</p>
        <div className="flex flex-wrap gap-2">
          {status.active_drones.length === 0 ? (
            <span className="text-sm text-slate-500">No active tracks</span>
          ) : (
            status.active_drones.map((id) => (
              <span
                key={id}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-600/60 bg-slate-800/60 px-2.5 py-1 text-sm text-slate-200"
              >
                <Plane size={13} className="text-accent-400" /> #{id}
              </span>
            ))
          )}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-slate-700/50 pt-3 text-xs text-slate-500">
        <span>Polling /status · /alerts every 2s</span>
        <span className={connected ? 'text-emerald-400' : 'text-red-400'}>
          {connected ? 'live feed' : 'mock fallback'}
        </span>
      </div>
    </div>
  );
}
