import { useEffect, useRef, useState } from 'react';
import { SystemMetrics } from '../types/telemetry';
import { Thresholds } from '../utils/thresholds';

export interface ActiveAlert {
  metric: 'cpuUsage' | 'ramUsage' | 'diskUsage';
  label: string;
  value: number;
  threshold: number;
}

const METRIC_LABELS: Record<ActiveAlert['metric'], string> = {
  cpuUsage: 'CPU',
  ramUsage: 'RAM',
  diskUsage: 'Disk',
};

function notify(nodeLabel: string, alert: ActiveAlert) {
  if (typeof Notification === 'undefined') return;
  if (Notification.permission !== 'granted') return;

  new Notification(`${nodeLabel}: high ${alert.label} usage`, {
    body: `${alert.label} at ${alert.value.toFixed(1)}% (threshold ${alert.threshold}%)`,
    tag: `${nodeLabel}-${alert.metric}`,
  });
}

export function useThresholdAlerts(
  nodeLabel: string,
  latest: SystemMetrics | null,
  thresholds: Thresholds
) {
  const [active, setActive] = useState<ActiveAlert[]>([]);
  const wasActiveRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!latest) return;

    const checks: ActiveAlert[] = [];
    (['cpuUsage', 'ramUsage', 'diskUsage'] as const).forEach((metric) => {
      const value = latest[metric];
      const threshold = thresholds[metric];
      if (value >= threshold) {
        checks.push({ metric, label: METRIC_LABELS[metric], value, threshold });
      }
    });

    const stillActive = new Set(checks.map((c) => c.metric));
    checks.forEach((alert) => {
      if (!wasActiveRef.current.has(alert.metric)) {
        notify(nodeLabel, alert);
      }
    });
    wasActiveRef.current = stillActive;

    setActive(checks);
  }, [latest, thresholds, nodeLabel]);

  return active;
}

export function requestNotificationPermission(): void {
  if (typeof Notification === 'undefined') return;
  if (Notification.permission === 'default') {
    Notification.requestPermission();
  }
}