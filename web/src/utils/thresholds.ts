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