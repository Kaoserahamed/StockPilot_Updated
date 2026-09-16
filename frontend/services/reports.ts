/**
 * Reporting service (FR-23): tabular reports with CSV / Excel / PDF export.
 *
 * `format=json` returns the table; every other format is a binary download,
 * so those helpers expose the request config for `downloadBlob` in `lib/api`.
 */

import { api } from '@/lib/api';
import type { ExportFormat, ProfitSummary, ReportKind, ReportTable } from '@/types';

export interface ReportQuery {
  preset?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
}

function queryString(query: ReportQuery, format: ExportFormat = 'json'): string {
  const params = new URLSearchParams({ format });
  if (query.preset) params.set('preset', query.preset);
  if (query.date_from) params.set('date_from', query.date_from);
  if (query.date_to) params.set('date_to', query.date_to);
  if (query.limit) params.set('limit', String(query.limit));
  return params.toString();
}

/** Fetch a report as structured rows (`format=json`). */
export async function report(
  kind: ReportKind,
  query: ReportQuery = {}
): Promise<ReportTable | ProfitSummary> {
  const { data } = await api.get<ReportTable | ProfitSummary>(
    `/reports/${kind}?${queryString(query)}`
  );
  return data;
}

/** Path for a binary export, ready for `downloadBlob`. */
export function reportExportPath(
  kind: ReportKind,
  format: Exclude<ExportFormat, 'json'>,
  query: ReportQuery = {}
): string {
  return `/reports/${kind}?${queryString(query, format)}`;
}

/** FR-23.8: the dedicated profit PDF endpoint. */
export function profitPdfPath(preset: string = 'month'): string {
  return `/reports/profit/pdf?preset=${preset}`;
}
