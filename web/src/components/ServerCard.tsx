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
    </div>
  );
};

export default ServerCard;