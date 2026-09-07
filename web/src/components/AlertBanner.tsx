import React from 'react';
import { ActiveAlert } from '../hooks/useThresholdAlerts';

interface Props {
  alerts: ActiveAlert[];
}

export const AlertBanner: React.FC<Props> = ({ alerts }) => {
  if (alerts.length === 0) return null;

  return (
    <div className="error-alert" style={{ marginBottom: '16px' }}>
      {alerts.map((alert) => (
        <div key={alert.metric}>
          High {alert.label} usage: {alert.value.toFixed(1)}% (threshold {alert.threshold}%)
        </div>
      ))}
    </div>
  );
};

export default AlertBanner;