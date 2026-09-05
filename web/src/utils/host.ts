export function normalizeHost(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, '');
  if (!trimmed) throw new Error('Host endpoint required.');

  const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;

  try {
    new URL(withScheme);
  } catch {
    throw new Error(`Invalid host endpoint: ${raw}`);
  }

  return withScheme;
}