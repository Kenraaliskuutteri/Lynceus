export interface Thresholds {
  cpuUsage: number;
  ramUsage: number;
  diskUsage: number;
}

export const DEFAULT_THRESHOLDS: Thresholds = {
  cpuUsage: 90,
  ramUsage: 90,
  diskUsage: 90,
};

const STORAGE_KEY = 'lynceus_thresholds';

export function loadThresholds(): Thresholds {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return DEFAULT_THRESHOLDS;

  try {
    const parsed = JSON.parse(raw);
    return {
      cpuUsage: typeof parsed.cpuUsage === 'number' ? parsed.cpuUsage : DEFAULT_THRESHOLDS.cpuUsage,
      ramUsage: typeof parsed.ramUsage === 'number' ? parsed.ramUsage : DEFAULT_THRESHOLDS.ramUsage,
      diskUsage: typeof parsed.diskUsage === 'number' ? parsed.diskUsage : DEFAULT_THRESHOLDS.diskUsage,
    };
  } catch {
    return DEFAULT_THRESHOLDS;
  }
}

export function saveThresholds(thresholds: Thresholds): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(thresholds));
}