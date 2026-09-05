import React from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { SystemMetrics } from '../../types/telemetry';

interface Props {
  data: SystemMetrics[];
}

export const CpuChart: React.FC<Props> = ({ data }) => {
  const chartData = data.map((m) => ({
    time: new Date(m.timestamp).toLocaleTimeString(),
    cpu: m.cpuUsage,
  }));

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-kicker">CPU</span>
        <h2>Utilization</h2>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
          <XAxis dataKey="time" stroke="#a0b2c6" fontSize={11} minTickGap={30} />
          <YAxis stroke="#a0b2c6" fontSize={11} domain={[0, 100]} unit="%" />
          <Tooltip contentStyle={{ background: '#121212', border: '1px solid #2a2a2a' }} />
          <Line type="monotone" dataKey="cpu" stroke="#7cc2ff" dot={false} strokeWidth={2} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default CpuChart;