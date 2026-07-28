export type ThreatLevel = 'low' | 'medium' | 'high' | 'critical';

export interface StatusResponse {
  threat_level: ThreatLevel;
  active_drones: number[];
  requires_approval: boolean;
}

export interface Alert {
  drone_id: number;
  threat_level: ThreatLevel;
  risk_score: number;
  current_position: [number, number, number];
  speed: number;
  confidence: number;
  reason: string;
}

export interface ChatMessage {
  id: string;
  sender: 'operator' | 'coordinator';
  text: string;
  timestamp: number;
}

export const THREAT_COLORS: Record<ThreatLevel, { text: string; bg: string; border: string; dot: string; label: string }> = {
  low:      { text: 'text-emerald-300', bg: 'bg-emerald-500/15', border: 'border-emerald-400/40', dot: '#22c55e', label: 'LOW' },
  medium:   { text: 'text-yellow-300',  bg: 'bg-yellow-500/15',  border: 'border-yellow-400/40',  dot: '#eab308', label: 'MEDIUM' },
  high:     { text: 'text-orange-300',  bg: 'bg-orange-500/15',  border: 'border-orange-400/40',  dot: '#f97316', label: 'HIGH' },
  critical: { text: 'text-red-300',     bg: 'bg-red-500/15',     border: 'border-red-400/40',     dot: '#ef4444', label: 'CRITICAL' },
};

