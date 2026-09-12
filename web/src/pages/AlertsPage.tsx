import React, { useEffect, useState } from 'react';
import { AlertEvent, AlertConfig } from '../types/telemetry';
import { fetchAlerts, fetchAlertConfig, triggerWebhookTest } from '../services/api';

const METRIC_LABELS: Record<string, string> = {
  cpu_usage: 'CPU',
  ram_usage: 'RAM',
  disk_usage: 'Disk',
};

type FilterStatus = 'all' | 'triggered' | 'resolved';

export const AlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [config, setConfig] = useState<AlertConfig | null>(null);
  const [filter, setFilter] = useState<FilterStatus>('all');
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);

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

      fetchAlertConfig()
        .then((cfg) => {
          if (!cancelled) setConfig(cfg);
        })
        .catch(() => {});
    };

    load();
    const interval = setInterval(load, 10000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const handleTestWebhook = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await triggerWebhookTest();
      setTestResult(res.message);
    } catch (err) {
      setTestResult(err instanceof Error ? err.message : 'Failed to trigger webhook test');
    } finally {
      setIsTesting(false);
    }
  };

  const activeCount = alerts.filter((a) => a.status === 'triggered').length;
  const filteredAlerts = alerts.filter((a) => {
    if (filter === 'all') return true;
    return a.status === filter;
  });

  return (
    <div className="content-page" style={{ padding: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ margin: 0 }}>Alert History & Dispatcher</h2>
          <div style={{ display: 'flex', gap: '8px', marginTop: '6px', alignItems: 'center' }}>
            <span className="panel-kicker" style={{ margin: 0 }}>
              {activeCount} ACTIVE
            </span>
            <span
              className="panel-kicker"
              style={{
                margin: 0,
                color: config?.webhook_configured ? '#34d399' : '#9ca3af',
              }}
            >
              WEBHOOK: {config?.webhook_configured ? config.webhook_format.toUpperCase() : 'NONE'}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {config?.webhook_configured && (
            <button
              className="secondary-button"
              onClick={handleTestWebhook}
              disabled={isTesting}
              style={{ fontSize: '0.8rem' }}
            >
              {isTesting ? 'Sending...' : 'Test Webhook'}
            </button>
          )}

          <div style={{ display: 'flex', gap: '4px' }}>
            {(['all', 'triggered', 'resolved'] as const).map((f) => (
              <button
                key={f}
                className="secondary-button"
                style={{
                  fontSize: '0.8rem',
                  fontWeight: filter === f ? 700 : 400,
                  borderColor: filter === f ? '#7cc2ff' : undefined,
                }}
                onClick={() => setFilter(f)}
              >
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {testResult && (
        <div className="panel" style={{ marginBottom: '16px', borderColor: '#3b82f6' }}>
          <p style={{ margin: 0, fontSize: '0.85rem' }}>{testResult}</p>
        </div>
      )}

      {error && <div className="error-alert">{error}</div>}

      {filteredAlerts.length === 0 ? (
        <div className="panel">
          <div className="panel-header">
            <span className="panel-kicker">No Incidents</span>
            <h2>Clean Slate</h2>
          </div>
          <p>No alerts match the current filter.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '12px' }}>
          {filteredAlerts.map((alert) => (
            <div
              key={alert.id}
              className="panel"
              style={{
                borderLeft: alert.status === 'triggered' ? '4px solid #ef4444' : '4px solid #10b981',
              }}
            >
              <div className="panel-header">
                <span
                  className="panel-kicker"
                  style={{ color: alert.status === 'triggered' ? '#ef4444' : '#10b981' }}
                >
                  {alert.status === 'triggered' ? 'ACTIVE' : 'RESOLVED'}
                </span>
                <h2>
                  {alert.serverId} &mdash; {METRIC_LABELS[alert.metric] ?? alert.metric}
                </h2>
              </div>
              <p>
                <strong>{alert.value.toFixed(1)}%</strong> (threshold {alert.threshold}%) &mdash; triggered{' '}
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