import { ServerNode, SystemMetrics, AlertEvent, AlertConfig, WebhookTestResult } from '../types/telemetry';
import { isValidHeaderValue } from '../utils/validation';

function getHost(): string | null {
  return localStorage.getItem('lynceus_host');
}

function getHeaders(): HeadersInit {
  const key = localStorage.getItem('lynceus_key');
  if (!key) return {};
  if (!isValidHeaderValue(key)) {
    throw new Error('Stored API key contains invalid characters. Disconnect and reconnect.');
  }
  return { Authorization: `Bearer ${key}` };
}

export async function fetchServers(): Promise<ServerNode[]> {
  const host = getHost();
  if (!host) throw new Error('No host configured');

  const response = await fetch(`${host}/api/v1/servers`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch servers: ${response.status}`);
  }

  return response.json();
}

export async function fetchHistory(serverId: string, minutes = 60): Promise<SystemMetrics[]> {
  const host = getHost();
  if (!host) throw new Error('No host configured');

  const response = await fetch(`${host}/api/v1/servers/${serverId}/history?minutes=${minutes}`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch history: ${response.status}`);
  }

  return response.json();
}

export async function fetchAlerts(serverId?: string, status?: string): Promise<AlertEvent[]> {
  const host = getHost();
  if (!host) throw new Error('No host configured');

  const params = new URLSearchParams();
  if (serverId) params.append('server_id', serverId);
  if (status) params.append('status', status);

  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await fetch(`${host}/api/v1/alerts${query}`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch alerts: ${response.status}`);
  }

  return response.json();
}

export async function fetchAlertConfig(): Promise<AlertConfig> {
  const host = getHost();
  if (!host) throw new Error('No host configured');

  const response = await fetch(`${host}/api/v1/alerts/config`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch alert config: ${response.status}`);
  }

  return response.json();
}

export async function triggerWebhookTest(): Promise<WebhookTestResult> {
  const host = getHost();
  if (!host) throw new Error('No host configured');

  const response = await fetch(`${host}/api/v1/alerts/test-webhook`, {
    method: 'POST',
    headers: getHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to trigger webhook test: ${response.status}`);
  }

  return response.json();
}