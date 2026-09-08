import React from 'react';
import { SystemMetrics } from '../types/telemetry';

interface Stat {
  min: number;
  max: number;
  avg: number;
}

function computeStats(values: number[]): Stat {
  if (values.length === 0) return { min: 0, max: 0, avg: 0 };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  return { min, max, avg };
}

interface Props {
  data: SystemMetrics[];
}

export const MetricStats: React.FC<Props> = ({ data }) => {
  const rows: { label: string; unit: string; stat: Stat }[] = [
    { label: 'CPU', unit: '%', stat: computeStats(data.map((m) => m.cpuUsage)) },
    { label: 'RAM', unit: '%', stat: computeStats(data.map((m) => m.ramUsage)) },
    { label: 'Net RX', unit: 'kb/s', stat: computeStats(data.map((m) => m.networkRxKb)) },
    { label: 'Net TX', unit: 'kb/s', stat: computeStats(data.map((m) => m.networkTxKb)) },
  ];

  return (
    <div className="panel" style={{ marginBottom: '16px' }}>
      <div className="panel-header">
        <span className="panel-kicker">Session</span>
        <h2>Min / Avg / Max</h2>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
        {rows.map((row) => (
          <div key={row.label}>
            <div style={{ color: '#a0b2c6', fontSize: '12px', marginBottom: '4px' }}>{row.label}</div>
            <div>
              {row.stat.min.toFixed(1)} / {row.stat.avg.toFixed(1)} / {row.stat.max.toFixed(1)} {row.unit}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MetricStats;