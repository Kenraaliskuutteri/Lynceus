import React, { useState } from 'react';
import { Thresholds, saveThresholds } from '../utils/thresholds';
import { requestNotificationPermission } from '../hooks/useThresholdAlerts';

interface Props {
  thresholds: Thresholds;
  onChange: (thresholds: Thresholds) => void;
}

export const ThresholdSettings: React.FC<Props> = ({ thresholds, onChange }) => {
  const [open, setOpen] = useState(false);

  const update = (field: keyof Thresholds, value: string) => {
    const parsed = Number(value);
    if (Number.isNaN(parsed)) return;

    const next = { ...thresholds, [field]: parsed };
    onChange(next);
    saveThresholds(next);
  };

  return (
    <div className="panel" style={{ marginBottom: '16px' }}>
      <div
        className="panel-header"
        style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between' }}
        onClick={() => {
          setOpen((o) => !o);
          requestNotificationPermission();
        }}
      >
        <span className="panel-kicker">Alert Thresholds</span>
        <h2>{open ? '▾' : '▸'}</h2>
      </div>

      {open && (
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          <div className="form-group">
            <label>CPU %</label>
            <input type="number" min={1} max={100} value={thresholds.cpuUsage} onChange={(e) => update('cpuUsage', e.target.value)} />
          </div>
          <div className="form-group">
            <label>RAM %</label>
            <input type="number" min={1} max={100} value={thresholds.ramUsage} onChange={(e) => update('ramUsage', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Disk %</label>
            <input type="number" min={1} max={100} value={thresholds.diskUsage} onChange={(e) => update('diskUsage', e.target.value)} />
          </div>
        </div>
      )}
    </div>
  );
};

export default ThresholdSettings;