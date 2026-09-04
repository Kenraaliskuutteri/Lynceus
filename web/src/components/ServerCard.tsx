// src/components/ServerCard.tsx
import React from 'react';
import { ServerNode } from '../types/telemetry';

interface Props {
  node: ServerNode;
}

export const ServerCard: React.FC<Props> = ({ node }) => {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-kicker">ONLINE</span>
        <h2>{node.hostname}</h2>
      </div>
      {/* Fallback to node.id or host if ip isn't in your type definition */}
      <p>ID: <code>{node.id}</code></p>
    </div>
  );
};

export default ServerCard;