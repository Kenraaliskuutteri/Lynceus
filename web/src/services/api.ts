import { ServerNode } from '../types/telemetry';
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