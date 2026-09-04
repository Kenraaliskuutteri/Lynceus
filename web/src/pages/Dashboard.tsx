import React from 'react';
import { ServerNode } from '../types/telemetry';
import { ServerCard } from '../components/ServerCard';

interface DashboardProps {
  nodes?: ServerNode[];
}

export const Dashboard: React.FC<DashboardProps> = ({ nodes = [] }) => {
  return (
    <div className="dashboard-page">
      <div className="content-page" style={{ padding: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2>Cluster Telemetry</h2>
          <span className="panel-kicker" style={{ margin: 0 }}>
            {nodes.length} {nodes.length === 1 ? 'NODE' : 'NODES'} ACTIVE
          </span>
        </div>

        {nodes.length === 0 ? (
          <div className="panel" style={{ marginTop: '20px' }}>
            <div className="panel-header">
              <span className="panel-kicker">Inactive Stream</span>
              <h2>No Live Telemetry</h2>
            </div>
            <p style={{ marginBottom: '16px' }}>
              Run the C collector daemon on target nodes to begin streaming JSON frames over WebSocket.
            </p>
            <pre className="cmd-block">
              <code>
                <span className="prompt-root">root@node:~#</span> ./lynceus-daemon --endpoint http://127.0.0.1:8000
              </code>
            </pre>
          </div>
        ) : (
          <div 
            style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
              gap: '20px', 
              marginTop: '20px' 
            }}
          >
            {nodes.map((node) => (
              <ServerCard key={node.id || node.hostname} node={node} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;