import { Table2 } from 'lucide-react';
import type { Alert } from '@/types';
import { THREAT_COLORS } from '@/types';

interface AlertsTableProps {
  alerts: Alert[];
}

export default function AlertsTable({ alerts }: AlertsTableProps) {
  return (
    <div className="glass rounded-xl p-4">
      <h3 className="display mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-200">
        <Table2 size={16} className="text-accent-400" /> Active Alerts
      </h3>
      <div className="overflow-x-auto scroll-thin">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-700/60 text-[11px] uppercase tracking-wider text-slate-500">
              <th className="py-2 pr-3 font-medium">Drone</th>
              <th className="py-2 pr-3 font-medium">Threat</th>
              <th className="py-2 pr-3 font-medium">Risk</th>
              <th className="py-2 pr-3 font-medium">Speed</th>
              <th className="py-2 pr-3 font-medium">Confidence</th>
              <th className="py-2 font-medium">Reason</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-6 text-center text-slate-500">
                  No active alerts
                </td>
              </tr>
            ) : (
              alerts.map((a) => {
                const c = THREAT_COLORS[a.threat_level];
                return (
                  <tr
                    key={a.drone_id}
                    className="border-b border-slate-800/60 transition hover:bg-slate-800/40"
                  >
                    <td className="py-2.5 pr-3 font-medium text-slate-200">#{a.drone_id}</td>
                    <td className="py-2.5 pr-3">
                      <span className={`inline-flex rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${c.bg} ${c.border} ${c.text}`}>
                        {c.label}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-700">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${Math.min(100, a.risk_score)}%`, backgroundColor: c.dot }}
                          />
                        </div>
                        <span className="tabular-nums text-slate-300">{a.risk_score.toFixed(1)}</span>
                      </div>
                    </td>
                    <td className="py-2.5 pr-3 tabular-nums text-slate-300">{a.speed.toFixed(1)}<span className="text-slate-500"> m/s</span></td>
                    <td className="py-2.5 pr-3 tabular-nums text-slate-300">{(a.confidence * 100).toFixed(0)}%</td>
                    <td className="py-2.5 text-slate-400">{a.reason}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
