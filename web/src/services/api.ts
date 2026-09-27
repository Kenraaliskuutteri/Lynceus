import { ServerNode, SystemMetrics, AlertEvent, AlertConfig, WebhookTestResult, ServerUptime } from '../types/telemetry';

export type Role = 'admin' | 'viewer';

interface SessionResponse {
  access_token: string;
  username: string;
  role: Role;
}

let accessToken: string | null = null;
let currentUsername: string | null = null;
let currentRole: Role | null = null;
let onSessionExpired: (() => void) | null = null;

export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler;
}

export function getSession(): { username: string | null; role: Role | null } {
  return { username: currentUsername, role: currentRole };
}

function applySession(data: SessionResponse): void {
  accessToken = data.access_token;
  currentUsername = data.username;
  currentRole = data.role;
}

function clearSession(): void {
  accessToken = null;
  currentUsername = null;
  currentRole = null;
}

function getHost(): string | null {
  return localStorage.getItem('lynceus_host');
}

function readCsrfCookie(): string {
  const match = document.cookie.match(/(?:^|;\s*)lynceus_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}

export async function login(host: string, username: string, password: string): Promise<{ username: string; role: Role }> {
  const response = await fetch(`${host}/api/v1/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Login failed: ${response.status}`);
  }

  const data: SessionResponse = await response.json();
  applySession(data);
  return { username: data.username, role: data.role };
}

export async function refreshSession(host: string): Promise<boolean> {
  const response = await fetch(`${host}/api/v1/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRF-Token': readCsrfCookie() },
  });

  if (!response.ok) {
    clearSession();
    return false;
  }

  applySession(await response.json());
  return true;
}

export async function logoutSession(): Promise<void> {
  const host = getHost();
  if (host) {
    await fetch(`${host}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'X-CSRF-Token': readCsrfCookie() },
    }).catch(() => {});
  }
  clearSession();
}

async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const host = getHost();
  if (!host) throw new Error('No host configured');

  const doFetch = () =>
    fetch(`${host}${path}`, {
      ...init,
      headers: {
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...(init.headers || {}),
      },
    });

  let response = await doFetch();

  if (response.status === 401 && accessToken !== null) {
    const refreshed = await refreshSession(host);
    if (refreshed) {
      response = await doFetch();
    } else if (onSessionExpired) {
      onSessionExpired();
    }
  }

  return response;
}

export async function fetchServers(): Promise<ServerNode[]> {
  const response = await authFetch('/api/v1/servers');
  if (!response.ok) throw new Error(`Failed to fetch servers: ${response.status}`);
  return response.json();
}

export async function fetchHistory(serverId: string, minutes = 60): Promise<SystemMetrics[]> {
  const response = await authFetch(`/api/v1/servers/${serverId}/history?minutes=${minutes}`);
  if (!response.ok) throw new Error(`Failed to fetch history: ${response.status}`);
  return response.json();
}

export async function fetchAlerts(serverId?: string, status?: string): Promise<AlertEvent[]> {
  const params = new URLSearchParams();
  if (serverId) params.append('server_id', serverId);
  if (status) params.append('status', status);
  const query = params.toString() ? `?${params.toString()}` : '';

  const response = await authFetch(`/api/v1/alerts${query}`);
  if (!response.ok) throw new Error(`Failed to fetch alerts: ${response.status}`);
  return response.json();
}

export async function acknowledgeAlert(alertId: number): Promise<AlertEvent> {
  const response = await authFetch(`/api/v1/alerts/${alertId}/acknowledge`, { method: 'POST' });
  if (!response.ok) throw new Error(`Failed to acknowledge alert: ${response.status}`);
  return response.json();
}

export async function unacknowledgeAlert(alertId: number): Promise<AlertEvent> {
  const response = await authFetch(`/api/v1/alerts/${alertId}/unacknowledge`, { method: 'POST' });
  if (!response.ok) throw new Error(`Failed to unacknowledge alert: ${response.status}`);
  return response.json();
}

export async function fetchUptime(serverId: string, days = 30): Promise<ServerUptime> {
  const response = await authFetch(`/api/v1/servers/${serverId}/uptime?days=${days}`);
  if (!response.ok) throw new Error(`Failed to fetch uptime: ${response.status}`);
  return response.json();
}

export async function fetchAlertConfig(): Promise<AlertConfig> {
  const response = await authFetch('/api/v1/alerts/config');
  if (!response.ok) throw new Error(`Failed to fetch alert config: ${response.status}`);
  return response.json();
}

export async function triggerWebhookTest(): Promise<WebhookTestResult> {
  const response = await authFetch('/api/v1/alerts/test-webhook', { method: 'POST' });
  if (!response.ok) throw new Error(`Failed to trigger webhook test: ${response.status}`);
  return response.json();
}