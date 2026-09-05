import React from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { SystemMetrics } from '../../types/telemetry';

interface Props {
  data: SystemMetrics[];
}

export const MemoryChart: React.FC<Props> = ({ data }) => {
  const chartData = data.map((m) => ({
    time: new Date(m.timestamp).toLocaleTimeString(),
    ram: m.ramUsage,
  }));

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-kicker">Memory</span>
        <h2>RAM Usage</h2>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
          <XAxis dataKey="time" stroke="#a0b2c6" fontSize={11} minTickGap={30} />
          <YAxis stroke="#a0b2c6" fontSize={11} domain={[0, 100]} unit="%" />
          <Tooltip contentStyle={{ background: '#121212', border: '1px solid #2a2a2a' }} />
          <Line type="monotone" dataKey="ram" stroke="#ff9d5c" dot={false} strokeWidth={2} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default MemoryChart;