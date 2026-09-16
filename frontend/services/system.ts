/**
 * Liveness/readiness probes (FR-38 platform hygiene).
 *
 * Exposed so the dashboard can show "API online" without a bespoke call, and
 * so deployment smoke checks have a typed entry point.
 */

import { rootApi } from '@/lib/api';

export interface LiveStatus {
  status: string;
  service: string;
  version: string;
  environment: string;
}

export interface DetailedStatus {
  status: string;
  database: string;
  error_tracking: {
    enabled: boolean;
    environment: string;
    release: string;
    total_captured: number;
    unique_fingerprints: number;
    last_error_at: string | null;
  };
  recent_errors: Record<string, unknown>[];
}

export async function liveness(): Promise<LiveStatus> {
  const { data } = await rootApi.get<LiveStatus>('/health');
  return data;
}

export async function detailedStatus(): Promise<DetailedStatus> {
  const { data } = await rootApi.get<DetailedStatus>('/health/detailed');
  return data;
}
