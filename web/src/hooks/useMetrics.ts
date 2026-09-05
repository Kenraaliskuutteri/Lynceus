import { useEffect, useMemo, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import { SystemMetrics } from '../types/telemetry';

const HISTORY_LIMIT = 60;

export function useMetrics(serverId: string | null) {
  const [history, setHistory] = useState<SystemMetrics[]>([]);

  const wsUrl = useMemo(() => {
    if (!serverId) return null;
    const host = localStorage.getItem('lynceus_host');
    if (!host) return null;
    const key = localStorage.getItem('lynceus_key') || '';
    const wsHost = host.replace(/^http/, 'ws');
    return `${wsHost}/api/v1/ws/metrics/${serverId}?key=${encodeURIComponent(key)}`;
  }, [serverId]);

  const { status, lastMessage } = useWebSocket(wsUrl);

  useEffect(() => {
    setHistory([]);
  }, [serverId]);

  useEffect(() => {
    if (!lastMessage) return;
    try {
      const metric: SystemMetrics = JSON.parse(lastMessage.data);
      setHistory((prev) => [...prev.slice(-(HISTORY_LIMIT - 1)), metric]);
    } catch {
      return;
    }
  }, [lastMessage]);

  return { history, status, latest: history[history.length - 1] ?? null };
}