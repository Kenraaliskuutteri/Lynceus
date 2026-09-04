export interface SystemMetrics {
  timestamp: number;
  cpuUsage: number;
  ramUsage: number;
  diskUsage: number;
  networkRxKb: number;
  networkTxKb: number;
}

export interface ServerNode {
  id: string;
  hostname: string;
  ipAddress: string;
  status: 'online' | 'offline' | 'error';
  lastSeen: string | null;
  metrics: SystemMetrics | null;
}