import { useEffect, useMemo, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import { SystemMetrics, AlertEvent } from '../types/telemetry';
import { fetchHistory, fetchAlerts } from '../services/api';

const LIVE_BUFFER_LIMIT = 500;

export function useMetrics(serverId: string | null, rangeMinutes: number = 60) {
  const [history, setHistory] = useState<SystemMetrics[]>([]);
  const [activeAlerts, setActiveAlerts] = useState<AlertEvent[]>([]);

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
    setActiveAlerts([]);
    if (!serverId) return;

    let cancelled = false;

    fetchHistory(serverId, rangeMinutes)
      .then((rows) => {
        if (!cancelled) setHistory(rows.slice(-LIVE_BUFFER_LIMIT));
      })
      .catch(() => {});

    fetchAlerts(serverId, 'triggered')
      .then((alerts) => {
        if (!cancelled) setActiveAlerts(alerts);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [serverId, rangeMinutes]);

  useEffect(() => {
    if (!lastMessage) return;
    try {
      const parsed = JSON.parse(lastMessage.data);
      if (parsed.type === 'alert' && parsed.event) {
        const event: AlertEvent = parsed.event;
        setActiveAlerts((prev) => {
          if (event.status === 'triggered') {
            const filtered = prev.filter((a) => a.metric !== event.metric);
            return [...filtered, event];
          } else if (event.status === 'resolved') {
            return prev.filter((a) => a.metric !== event.metric);
          }
          return prev;
        });
      } else if (typeof parsed.cpuUsage === 'number') {
        const metric: SystemMetrics = parsed;
        setHistory((prev) => [...prev.slice(-(LIVE_BUFFER_LIMIT - 1)), metric]);
      }
    } catch {
      return;
    }
  }, [lastMessage]);

  return {
    history,
    status,
    latest: history[history.length - 1] ?? null,
    activeAlerts,
  };
}