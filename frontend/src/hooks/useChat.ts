import { useCallback, useState } from 'react';
import type { ChatMessage } from '@/types';

const API_BASE = 'http://localhost:8000';

const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export function useChat() {
  // 1. Start with a clean, generic greeting instead of ghost drone data
  const [messages, setMessages] = useState<ChatMessage[]>([
    { 
      id: makeId(), 
      sender: 'coordinator', 
      text: 'Coordinator online. Standing by for operator instructions.', 
      timestamp: Date.now() 
    },
  ]);
  
  const [sending, setSending] = useState(false);

  const send = useCallback(async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || sending) return;
    
    // Add the operator's message to the UI immediately
    setMessages((m) => [...m, { id: makeId(), sender: 'operator', text: trimmed, timestamp: Date.now() }]);
    setSending(true);
    
    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed }),
      });
      
      if (!res.ok) throw new Error('Network response was not ok');
      
      const data = await res.json() as { answer?: string; response?: string; message?: string };
      const reply = data.answer ?? data.response ?? data.message ?? 'No response payload received.';
      
      // Add the real Coordinator Agent response to the UI
      setMessages((m) => [...m, { id: makeId(), sender: 'coordinator', text: reply, timestamp: Date.now() }]);
    } catch (error) {
      // 2. If the backend is offline, show a real error instead of a fake mock reply
      setMessages((m) => [...m, { 
        id: makeId(), 
        sender: 'coordinator', 
        text: 'System Error: Unable to reach Coordinator Agent API. Please ensure the backend is running.', 
        timestamp: Date.now() 
      }]);
    } finally {
      setSending(false);
    }
  }, [sending]);

  return { messages, send, sending };
}