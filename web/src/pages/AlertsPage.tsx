import React, { useEffect, useState } from 'react';
import { AlertEvent } from '../types/telemetry';
import { fetchAlerts } from '../services/api';

const METRIC_LABELS: Record<string, string> = {
  cpu_usage: 'CPU',
  ram_usage: 'RAM',
  disk_usage: 'Disk',
};

export const AlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = () => {
      fetchAlerts()
        .then((data) => {
          if (!cancelled) setAlerts(data);
        })
        .catch((err) => {
          if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load alerts');
        });
    };

    load();
    const interval = setInterval(load, 10000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const activeCount = alerts.filter((a) => a.status === 'triggered').length;

  return (
    <div className="content-page" style={{ padding: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2>Alert History</h2>
        <span className="panel-kicker" style={{ margin: 0 }}>
          {activeCount} ACTIVE
        </span>
      </div>

      {error && <div className="error-alert">{error}</div>}

      {alerts.length === 0 ? (
        <div className="panel">
          <div className="panel-header">
            <span className="panel-kicker">No Incidents</span>
            <h2>Clean Slate</h2>
          </div>
          <p>No threshold breaches recorded yet.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '12px' }}>
          {alerts.map((alert) => (
            <div key={alert.id} className="panel">
              <div className="panel-header">
                <span className="panel-kicker">{alert.status === 'triggered' ? 'ACTIVE' : 'RESOLVED'}</span>
                <h2>
                  {alert.serverId} &mdash; {METRIC_LABELS[alert.metric] ?? alert.metric}
                </h2>
              </div>
              <p>
                {alert.value.toFixed(1)}% (threshold {alert.threshold}%) &mdash; triggered{' '}
                {new Date(alert.triggeredAt).toLocaleString()}
                {alert.resolvedAt && <> &mdash; resolved {new Date(alert.resolvedAt).toLocaleString()}</>}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AlertsPage;