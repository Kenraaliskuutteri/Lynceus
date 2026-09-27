import React from 'react';
import { AlertEvent } from '../types/telemetry';
import { acknowledgeAlert, unacknowledgeAlert } from '../services/api';
import { useAuth } from '../context/AuthContext';

const METRIC_LABELS: Record<string, string> = {
  cpu_usage: 'CPU',
  ram_usage: 'RAM',
  disk_usage: 'Disk',
  offline: 'Connectivity',
};

interface Props {
  alerts: AlertEvent[];
}

function formatAlert(alert: AlertEvent): string {
  const label = METRIC_LABELS[alert.metric] ?? alert.metric;
  if (alert.metric === 'offline') {
    return `Offline for ${alert.value.toFixed(0)}s (limit ${alert.threshold.toFixed(0)}s)`;
  }
  return `High ${label} usage: ${alert.value.toFixed(1)}% (threshold ${alert.threshold}%)`;
}

export const AlertBanner: React.FC<Props> = ({ alerts }) => {
  const { role } = useAuth();
  if (alerts.length === 0) return null;

  const toggleAck = (alert: AlertEvent) => {
    if (alert.acknowledgedAt) {
      unacknowledgeAlert(alert.id).catch(() => {});
    } else {
      acknowledgeAlert(alert.id).catch(() => {});
    }
  };

  return (
    <div className="error-alert" style={{ marginBottom: '16px' }}>
      {alerts.map((alert) => (
        <div
          key={alert.id || alert.metric}
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            margin: '2px 0',
            opacity: alert.acknowledgedAt ? 0.55 : 1,
          }}
        >
          <span>
            <strong>{formatAlert(alert)}</strong>
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '11px', opacity: 0.85 }}>
              Triggered {new Date(alert.triggeredAt).toLocaleTimeString()}
            </span>
            {role === 'admin' && (
              <button
                className="secondary-button"
                style={{ fontSize: '11px', padding: '2px 8px' }}
                onClick={() => toggleAck(alert)}
              >
                {alert.acknowledgedAt ? 'Unack' : 'Ack'}
              </button>
            )}
          </span>
        </div>
      ))}
    </div>
  );
};

export default AlertBanner;