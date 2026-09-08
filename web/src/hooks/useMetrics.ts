import { useEffect, useMemo, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import { SystemMetrics } from '../types/telemetry';
import { fetchHistory } from '../services/api';

const LIVE_BUFFER_LIMIT = 500;

export function useMetrics(serverId: string | null, rangeMinutes: number = 60) {
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
    if (!serverId) return;

    let cancelled = false;

    fetchHistory(serverId, rangeMinutes)
      .then((rows) => {
        if (!cancelled) setHistory(rows.slice(-LIVE_BUFFER_LIMIT));
      })
      .catch(() => {
        return;
      });

    return () => {
      cancelled = true;
    };
  }, [serverId, rangeMinutes]);

  useEffect(() => {
    if (!lastMessage) return;
    try {
      const metric: SystemMetrics = JSON.parse(lastMessage.data);
      setHistory((prev) => [...prev.slice(-(LIVE_BUFFER_LIMIT - 1)), metric]);
    } catch {
      return;
    }
  }, [lastMessage]);

  return { history, status, latest: history[history.length - 1] ?? null };
}