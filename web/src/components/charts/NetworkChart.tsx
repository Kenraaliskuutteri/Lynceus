import React from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';
import { SystemMetrics } from '../../types/telemetry';

interface Props {
  data: SystemMetrics[];
}

export const NetworkChart: React.FC<Props> = ({ data }) => {
  const chartData = data.map((m) => ({
    time: new Date(m.timestamp).toLocaleTimeString(),
    rx: m.networkRxKb,
    tx: m.networkTxKb,
  }));

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-kicker">Network</span>
        <h2>Throughput</h2>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
          <XAxis dataKey="time" stroke="#a0b2c6" fontSize={11} minTickGap={30} />
          <YAxis stroke="#a0b2c6" fontSize={11} unit="kb/s" />
          <Tooltip contentStyle={{ background: '#121212', border: '1px solid #2a2a2a' }} />
          <Legend />
          <Line type="monotone" dataKey="rx" name="RX" stroke="#5cffb0" dot={false} strokeWidth={2} isAnimationActive={false} />
          <Line type="monotone" dataKey="tx" name="TX" stroke="#ff5c8a" dot={false} strokeWidth={2} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default NetworkChart;