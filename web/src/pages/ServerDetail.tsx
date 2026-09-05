import React from 'react';
import { ServerNode } from '../types/telemetry';
import { useMetrics } from '../hooks/useMetrics';
import { CpuChart } from '../components/charts/CpuChart';
import { MemoryChart } from '../components/charts/MemoryChart';
import { NetworkChart } from '../components/charts/NetworkChart';

interface Props {
  node: ServerNode;
  onBack: () => void;
}

export const ServerDetail: React.FC<Props> = ({ node, onBack }) => {
  const { history, status } = useMetrics(node.id);

  return (
    <div className="content-page" style={{ padding: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <button className="secondary-button" onClick={onBack} style={{ marginBottom: '12px' }}>
            &larr; Back
          </button>
          <h2 style={{ margin: 0 }}>{node.hostname}</h2>
          <p style={{ margin: '4px 0 0', color: '#a0b2c6' }}>{node.ipAddress}</p>
        </div>
        <span className="panel-kicker">{status === 'open' ? 'STREAMING' : status.toUpperCase()}</span>
      </div>

      {history.length === 0 ? (
        <div className="panel">
          <div className="panel-header">
            <span className="panel-kicker">Inactive Stream</span>
            <h2>Waiting for Telemetry</h2>
          </div>
          <p>No metric frames received yet for this node.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '20px' }}>
          <CpuChart data={history} />
          <MemoryChart data={history} />
          <NetworkChart data={history} />
        </div>
      )}
    </div>
  );
};

export default ServerDetail;