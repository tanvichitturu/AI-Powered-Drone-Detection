import { useState } from 'react';
import { Home, Radar, Wifi, WifiOff, Camera, VideoOff, ShieldAlert, CheckCircle, Eye, Footprints, X } from 'lucide-react';
import { usePolling } from '@/hooks/usePolling';
import ThreatStatus from '@/components/ThreatStatus';
import RadarPanel from '@/components/RadarPanel';
import AlertsTable from '@/components/AlertsTable';
import CoordinatorChat from '@/components/CoordinatorChat';

interface DashboardProps {
  onHome: () => void;
}

type EscalationAction = 'authorize' | 'monitor' | 'evacuate';
type Toast = { id: number; text: string; tone: 'red' | 'yellow' | 'orange' };

const ACTION_LABELS: Record<EscalationAction, string> = {
  authorize: 'AUTHORIZE transmitted to Response Planning Agent',
  monitor: 'MONITOR engaged — passive surveillance active',
  evacuate: 'EVACUATE protocol broadcast to all agents',
};
const ACTION_TONES: Record<EscalationAction, Toast['tone']> = { authorize: 'red', monitor: 'yellow', evacuate: 'orange' };

export default function Dashboard({ onHome }: DashboardProps) {
  const { status, alerts, connected, lastUpdated, refreshing, refresh } = usePolling();
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const pushToast = (text: string, tone: Toast['tone']) => {
    const id = Date.now();
    setToasts((t) => [...t, { id, text, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3200);
  };

  const handleAction = (action: EscalationAction) => {
    pushToast(ACTION_LABELS[action], ACTION_TONES[action]);
    setBannerDismissed(true);
  };

  const showBanner = status.requires_approval && !bannerDismissed;

  const [streamError, setStreamError] = useState(false);
  const streamUrl = "/video_feed";

  const handleStreamError = () => {
    setStreamError(true);
    // Auto-retry stream connection after 3 seconds
    setTimeout(() => {
      setStreamError(false);
    }, 3000);
  };

  const isStreamActive = connected && !streamError;

  return (
    <div className="min-h-screen bg-base-900 text-slate-200">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,rgba(14,165,233,0.12),transparent_50%)]" />

      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-slate-700/50 bg-base-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-5 py-3">
          <div className="flex items-center gap-4">
            <button onClick={onHome} className="btn-ghost !px-3 !py-1.5 text-xs">
              <Home size={14} /> Home
            </button>
            <div className="flex items-center gap-2">
              <Radar className="text-accent-400" size={18} />
              <h1 className="display text-base font-bold uppercase tracking-wider text-white">Defense Dashboard</h1>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden items-center gap-1.5 text-xs text-slate-400 sm:flex">
              {isStreamActive ? <Camera size={13} className="text-emerald-400" /> : <VideoOff size={13} className="text-slate-500" />}
              {isStreamActive ? 'Live AI Stream' : 'Stream Offline'}
            </span>
            <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${connected ? 'border-emerald-400/40 bg-emerald-500/10 text-emerald-300' : 'border-red-400/40 bg-red-500/10 text-red-300'}`}>
              {connected ? <Wifi size={13} /> : <WifiOff size={13} />}
              {connected ? 'Connected' : 'Unreachable'}
            </span>
          </div>
        </div>
      </header>

      <div className="relative z-10 mx-auto max-w-[1600px] px-5 py-4">
        {showBanner && (
          <div className="mb-4 animate-slide-down rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 backdrop-blur">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-3">
                <ShieldAlert className="animate-blink text-red-400" size={22} />
                <p className="text-sm font-semibold text-red-200">Critical threat requires operator decision.</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {([
                  ['authorize', 'Authorize', 'bg-red-600 hover:bg-red-500', CheckCircle],
                  ['monitor', 'Monitor', 'bg-yellow-500 hover:bg-yellow-400 text-yellow-950', Eye],
                  ['evacuate', 'Evacuate', 'bg-orange-500 hover:bg-orange-400', Footprints],
                ] as const).map(([action, label, cls, Icon]) => (
                  <button key={action} onClick={() => handleAction(action)} className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-white transition ${cls}`}>
                    <Icon size={14} /> {label}
                  </button>
                ))}
                <button onClick={() => setBannerDismissed(true)} className="inline-flex items-center gap-1.5 rounded-md border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-slate-500 hover:text-white">
                  <X size={14} /> Dismiss
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[3fr_2fr]">
          <div className="space-y-4">
            
            {/* Live camera feed */}
            <div className="glass overflow-hidden rounded-xl">
              <div className="flex items-center justify-between border-b border-slate-700/50 px-4 py-2.5">
                <h3 className="display flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-200">
                  <Camera size={16} className="text-accent-400" /> Live AI Feed
                </h3>
                <span className={`flex items-center gap-1.5 text-xs font-medium ${isStreamActive ? 'text-emerald-400' : 'text-red-400'}`}>
                  <span className={`h-2 w-2 rounded-full ${isStreamActive ? 'animate-blink bg-emerald-400' : 'bg-red-500'}`} />
                  {isStreamActive ? 'STREAMING' : 'OFFLINE'}
                </span>
              </div>
              <div className="relative aspect-video bg-black/60 flex items-center justify-center">
                
                {!streamError && (
                  <img
                    src={streamUrl}
                    alt="Live Tactical AI Stream"
                    className="h-full w-full object-cover"
                    onError={handleStreamError}
                    onLoad={() => setStreamError(false)}
                  />
                )}

                {(!connected || streamError) && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-slate-500 bg-black/80">
                    <VideoOff size={28} />
                    <p className="text-xs">Backend Unreachable / Stream Offline</p>
                  </div>
                )}

                {isStreamActive && (
                  <>
                    <div className="pointer-events-none absolute inset-0 ring-1 ring-inset ring-accent-400/20" />
                    <div className="pointer-events-none absolute left-3 top-3 flex items-center gap-1.5 rounded bg-black/60 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-400 border border-emerald-500/30">
                      <span className="h-1.5 w-1.5 animate-blink rounded-full bg-emerald-400" /> CAM-01
                    </div>
                    {/* Crosshair overlay */}
                    <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
                      <div className="h-16 w-px bg-accent-400/30" />
                      <div className="absolute left-1/2 top-1/2 h-px w-16 -translate-x-1/2 -translate-y-1/2 bg-accent-400/30" />
                    </div>
                  </>
                )}
              </div>
            </div>

            <ThreatStatus status={status} lastUpdated={lastUpdated} connected={connected} refreshing={refreshing} onRefresh={refresh} />
            <RadarPanel alerts={alerts} />
            <AlertsTable alerts={alerts} />
          </div>
          <div className="lg:h-[calc(100vh-9rem)] lg:sticky lg:top-20">
            <div className="h-[70vh] lg:h-full">
              <CoordinatorChat />
            </div>
          </div>
        </div>
      </div>

      {/* Toasts */}
      <div className="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 space-y-2">
        {toasts.map((t) => (
          <div key={t.id} className={`animate-slide-down flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium shadow-lg backdrop-blur ${t.tone === 'red' ? 'bg-red-600/90 text-white' : t.tone === 'yellow' ? 'bg-yellow-500/90 text-yellow-950' : 'bg-orange-500/90 text-white'}`}>
            <ShieldAlert size={15} /> {t.text}
          </div>
        ))}
      </div>
    </div>
  );
}