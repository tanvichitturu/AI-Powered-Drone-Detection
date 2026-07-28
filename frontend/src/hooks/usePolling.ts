import { useCallback, useEffect, useRef, useState } from 'react';
import type { Alert, StatusResponse } from '@/types';

const API_BASE = 'http://localhost:8000';
const POLL_INTERVAL = 2000;

// Default status when backend is unreachable
const DEFAULT_STATUS: StatusResponse = {
  threat_level: 'low', // Changed from 'SAFE' to match your ThreatLevel type
  requires_approval: false,
  active_drones: []
};

export function usePolling() {
  const [status, setStatus] = useState<StatusResponse>(DEFAULT_STATUS);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [connected, setConnected] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(Date.now());
  const [refreshing, setRefreshing] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const tick = useCallback(async (manual: boolean) => {
    if (manual) setRefreshing(true);
    const controller = new AbortController();
    abortRef.current?.abort();
    abortRef.current = controller;
    
    try {
      const [s, a] = await Promise.all([
        fetch(`${API_BASE}/status`, { signal: controller.signal }).then((r) => r.json()) as Promise<StatusResponse>,
        fetch(`${API_BASE}/alerts`, { signal: controller.signal }).then((r) => r.json()),
      ]);
      
      setStatus(s);
      
      // Safely handle both array responses and object responses (e.g. { alerts: [...] })
      const fetchedAlerts = Array.isArray(a) ? a : (a as any).alerts || [];
      setAlerts(fetchedAlerts);
      
      setConnected(true);
    } catch {
      // If the backend drops, clear the table and reset to safe defaults instead of mocks
      setStatus(DEFAULT_STATUS);
      setAlerts([]);
      setConnected(false);
    } finally {
      setLastUpdated(Date.now());
      setRefreshing(false);
    }
  }, []);

  const refresh = useCallback(() => void tick(true), [tick]);

  useEffect(() => {
    void tick(false);
    const id = setInterval(() => void tick(false), POLL_INTERVAL);
    return () => {
      clearInterval(id);
      abortRef.current?.abort();
    };
  }, [tick]);

  return { status, alerts, connected, lastUpdated, refreshing, refresh };
}