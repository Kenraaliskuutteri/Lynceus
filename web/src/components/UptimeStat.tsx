import React, { useEffect, useState } from 'react';
import { ServerUptime } from '../types/telemetry';
import { fetchUptime } from '../services/api';

interface Props {
  serverId: string;
  days?: number;
}

export const UptimeStat: React.FC<Props> = ({ serverId, days = 30 }) => {
  const [uptime, setUptime] = useState<ServerUptime | null>(null);

  useEffect(() => {
    let cancelled = false;
    setUptime(null);

    fetchUptime(serverId, days)
      .then((data) => {
        if (!cancelled) setUptime(data);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [serverId, days]);

  if (!uptime) return null;

  const downtimeMinutes = Math.round(uptime.downtimeSeconds / 60);

  return (
    <div className="panel" style={{ marginBottom: '16px' }}>
      <div className="panel-header">
        <span className="panel-kicker">Reliability</span>
        <h2>{uptime.uptimePercent.toFixed(2)}% uptime</h2>
      </div>
      <p style={{ margin: 0, color: '#a0b2c6' }}>
        Last {uptime.windowDays}d &middot; {uptime.incidentCount} incident{uptime.incidentCount === 1 ? '' : 's'}
        &middot; {downtimeMinutes}m downtime
      </p>
    </div>
  );
};

export default UptimeStat;