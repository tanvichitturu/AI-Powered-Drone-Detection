import { useState } from 'react';
import { Radar, ArrowRight, Power, ShieldCheck } from 'lucide-react';
import EntryModal from '@/components/EntryModal';

interface LandingProps {
  onEnter: () => void;
}

export default function Landing({ onEnter }: LandingProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="relative min-h-screen overflow-hidden bg-base-900">
      {/* ambient gradient + static radar backdrop */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(14,165,233,0.18),transparent_55%)]" />
      <div className="pointer-events-none absolute -left-40 top-1/3 h-96 w-96 rounded-full bg-accent-500/10 blur-3xl" />
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-20">
        <svg width={560} height={560} viewBox="0 0 560 560" className="max-w-none">
          {[0.25, 0.5, 0.75, 1].map((r) => (
            <circle key={r} cx={280} cy={280} r={270 * r} fill="none" stroke="#0ea5e9" strokeOpacity="0.25" strokeWidth="1" />
          ))}
          {[0, 45, 90, 135].map((deg) => {
            const rad = (deg * Math.PI) / 180;
            return <line key={deg} x1={280} y1={280} x2={280 + Math.cos(rad) * 270} y2={280 + Math.sin(rad) * 270} stroke="#0ea5e9" strokeOpacity="0.15" strokeWidth="1" />;
          })}
          <circle cx={280} cy={280} r="4" fill="#0ea5e9" fillOpacity="0.5" />
          <circle cx={280} cy={280} r="9" fill="none" stroke="#0ea5e9" strokeOpacity="0.3" />
        </svg>
      </div>

      <div className="relative z-10 flex min-h-screen flex-col">
        <header className="flex items-center justify-between px-6 py-5">
          <div className="flex items-center gap-2">
            <Radar className="text-accent-400" size={22} />
            <span className="display text-sm font-semibold tracking-[0.2em] text-slate-200">
              DRONE DEFENSE SYSTEM
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="h-2 w-2 rounded-full bg-slate-600" /> SYSTEM STANDBY
          </div>
        </header>

        <main className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-slate-600/50 bg-slate-800/50 px-4 py-1.5 text-xs font-medium uppercase tracking-wider text-slate-400">
            <Power size={14} /> System Inactive
          </div>
          <h1 className="display max-w-4xl text-4xl font-extrabold leading-tight text-white sm:text-6xl">
            Drone Defense
            <span className="block bg-gradient-to-r from-accent-400 to-cyan-300 bg-clip-text text-transparent">
              Operational Interface
            </span>
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-relaxed text-slate-400 sm:text-lg">
            Real-time tracking, threat assessment, and coordinated counter-drone response — orchestrated by a
            collaborative agent crew under human authorization.
          </p>

          <button onClick={() => setModalOpen(true)} className="btn-primary mt-10 text-base">
            Enter Dashboard <ArrowRight size={18} />
          </button>

          <p className="mt-6 flex items-center gap-2 text-sm text-slate-500">
            <ShieldCheck size={14} className="text-slate-600" /> System activates upon entering the dashboard
          </p>
        </main>

        <footer className="mt-16 px-6 py-6 text-center text-xs text-slate-600">
          AI-Powered Drone Detection System
        </footer>
      </div>

      <EntryModal open={modalOpen} onClose={() => setModalOpen(false)} onEnter={onEnter} />
    </div>
  );
}
