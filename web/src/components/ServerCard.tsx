import React from 'react';
import { ServerNode } from '../types/telemetry';

interface Props {
  node: ServerNode;
  onSelect?: () => void;
}

export const ServerCard: React.FC<Props> = ({ node, onSelect }) => {
  return (
    <div className="panel" onClick={onSelect} style={{ cursor: onSelect ? 'pointer' : 'default' }}>
      <div className="panel-header">
        <span className="panel-kicker">{node.status.toUpperCase()}</span>
        <h2>{node.hostname}</h2>
      </div>
      <p>ID: <code>{node.id}</code></p>
      {node.metrics ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginTop: '8px' }}>
          <div>
            <div style={{ color: '#a0b2c6', fontSize: '12px', marginBottom: '4px' }}>CPU</div>
            <div>{node.metrics.cpuUsage.toFixed(1)}%</div>
          </div>
          <div>
            <div style={{ color: '#a0b2c6', fontSize: '12px', marginBottom: '4px' }}>RAM</div>
            <div>{node.metrics.ramUsage.toFixed(1)}%</div>
          </div>
          <div>
            <div style={{ color: '#a0b2c6', fontSize: '12px', marginBottom: '4px' }}>Disk</div>
            <div>{node.metrics.diskUsage.toFixed(1)}%</div>
          </div>
        </div>
      ) : (
        <p style={{ color: '#a0b2c6' }}>No telemetry yet</p>
      )}
    </div>
  );
};

export default ServerCard;