import React from 'react';
import { AlertEvent } from '../types/telemetry';

const METRIC_LABELS: Record<string, string> = {
  cpu_usage: 'CPU',
  ram_usage: 'RAM',
  disk_usage: 'Disk',
};

interface Props {
  alerts: AlertEvent[];
}

export const AlertBanner: React.FC<Props> = ({ alerts }) => {
  if (alerts.length === 0) return null;

  return (
    <div className="error-alert" style={{ marginBottom: '16px' }}>
      {alerts.map((alert) => (
        <div
          key={alert.id || alert.metric}
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '2px 0' }}
        >
          <span>
            <strong>High {METRIC_LABELS[alert.metric] ?? alert.metric} usage:</strong>{' '}
            {alert.value.toFixed(1)}% (threshold {alert.threshold}%)
          </span>
          <span style={{ fontSize: '11px', opacity: 0.85, marginLeft: '12px' }}>
            Triggered {new Date(alert.triggeredAt).toLocaleTimeString()}
          </span>
        </div>
      ))}
    </div>
  );
};

export default AlertBanner;