import { useEffect, useRef, useState } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import { useChat } from '@/hooks/useChat';

export default function CoordinatorChat() {
  const { messages, send, sending } = useChat();
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || sending) return;
    void send(input);
    setInput('');
  };

  return (
    <div className="glass flex h-full flex-col rounded-xl p-4">
      <div className="mb-3 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-500/15 text-accent-300">
          <Bot size={16} />
        </span>
        <div>
          <h3 className="display text-sm font-semibold uppercase tracking-wider text-slate-200">Coordinator</h3>
          <p className="text-[10px] uppercase tracking-wider text-emerald-400">online · AI agent</p>
        </div>
      </div>

      <div ref={scrollRef} className="scroll-thin flex-1 space-y-3 overflow-y-auto pr-1">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.sender === 'operator' ? 'justify-end' : 'justify-start'} animate-fade-in`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${
                m.sender === 'operator'
                  ? 'bg-accent-500 text-white rounded-br-sm'
                  : 'glass-accent text-slate-200 rounded-bl-sm'
              }`}
            >
              <div className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wider opacity-70">
                {m.sender === 'operator' ? <User size={10} /> : <Bot size={10} />}
                {m.sender}
              </div>
              <p className="leading-relaxed">{m.text}</p>
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="glass-accent flex items-center gap-2 rounded-2xl rounded-bl-sm px-3.5 py-2.5 text-sm text-slate-400">
              <Loader2 size={14} className="animate-spin" /> Coordinator is typing…
            </div>
          </div>
        )}
      </div>

      <form onSubmit={submit} className="mt-3 flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the coordinator…"
          className="flex-1 rounded-lg border border-slate-600/60 bg-slate-900/60 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none transition focus:border-accent-400 focus:ring-1 focus:ring-accent-400/40"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-accent-500 text-white transition hover:bg-accent-400 disabled:opacity-40"
          aria-label="Send"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
