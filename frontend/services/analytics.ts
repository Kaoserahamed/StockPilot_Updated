/**
 * Analytics service (FR-19..FR-22): dashboard KPIs plus product, customer and
 * supplier performance.
 */

import { api } from '@/lib/api';
import type { CustomerStat, Dashboard, ProductPerformance, SupplierStat } from '@/types';

export interface AnalyticsQuery {
  preset?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
}

function queryString(query: AnalyticsQuery): string {
  const params = new URLSearchParams();
  if (query.preset) params.set('preset', query.preset);
  if (query.date_from) params.set('date_from', query.date_from);
  if (query.date_to) params.set('date_to', query.date_to);
  if (query.limit) params.set('limit', String(query.limit));
  const built = params.toString();
  return built ? `?${built}` : '';
}

export interface SalesTrendPoint {
  period: string;
  orders: number;
  revenue: number;
}

export async function dashboard(query: AnalyticsQuery = {}): Promise<Dashboard> {
  const { data } = await api.get<Dashboard>(`/dashboard${queryString(query)}`);
  return data;
}

export interface ProductAnalytics {
  best_sellers: ProductPerformance[];
  low_performers: ProductPerformance[];
  all: ProductPerformance[];
}

export async function productAnalytics(query: AnalyticsQuery = {}): Promise<ProductAnalytics> {
  const { data } = await api.get<ProductAnalytics>(`/analytics/products${queryString(query)}`);
  return data;
}

export interface CustomerAnalytics {
  top_customers: CustomerStat[];
  returning: CustomerStat[];
  all: CustomerStat[];
}

export async function customerAnalytics(query: AnalyticsQuery = {}): Promise<CustomerAnalytics> {
  const { data } = await api.get<CustomerAnalytics>(`/analytics/customers${queryString(query)}`);
  return data;
}

export interface SupplierAnalytics {
  suppliers?: SupplierStat[];
  top_suppliers?: SupplierStat[];
  all?: SupplierStat[];
}

export async function supplierAnalytics(query: AnalyticsQuery = {}): Promise<SupplierAnalytics> {
  const { data } = await api.get<SupplierAnalytics>(`/analytics/suppliers${queryString(query)}`);
  return data;
}
