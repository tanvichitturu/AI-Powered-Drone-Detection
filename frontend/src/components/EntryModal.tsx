import { useEffect, useState } from 'react';
import { Camera, X, Loader2, Radar } from 'lucide-react';

interface EntryModalProps {
  open: boolean;
  onClose: () => void;
  onEnter: () => void;
}

export default function EntryModal({ open, onClose, onEnter }: EntryModalProps) {
  const [entering, setEntering] = useState(false);

  useEffect(() => { if (!open) setEntering(false); }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const enter = () => {
    setEntering(true);
    setTimeout(() => { onEnter(); setEntering(false); }, 600);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 animate-fade-in" onClick={onClose}>
      <div className="glass relative w-full max-w-lg rounded-2xl p-6 shadow-2xl animate-slide-down" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="absolute right-4 top-4 rounded-md p-1.5 text-slate-400 transition hover:bg-slate-700/60 hover:text-white" aria-label="Close">
          <X size={18} />
        </button>

        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-500/15 text-accent-300">
            <Radar size={20} />
          </div>
          <div>
            <h2 className="display text-lg font-bold text-white">Activate System</h2>
            <p className="text-xs text-slate-400">The defense system will access your webcam for live tracking.</p>
          </div>
        </div>

        <div className="glass-accent rounded-xl p-4 text-sm text-slate-300">
          <p className="mb-2 flex items-center gap-2 font-semibold text-accent-200"><Camera size={16} /> Webcam input</p>
          <p className="leading-relaxed">
            The system will request browser permission to access your webcam and stream live frames to the
            tracking pipeline. No frames leave your device in this preview.
          </p>
        </div>

        <button onClick={enter} disabled={entering} className="btn-primary mt-4 w-full">
          {entering ? <Loader2 size={18} className="animate-spin" /> : <Camera size={18} />}
          {entering ? 'Initializing Camera…' : 'Initialize Camera & Enter Dashboard'}
        </button>
      </div>
    </div>
  );
}
