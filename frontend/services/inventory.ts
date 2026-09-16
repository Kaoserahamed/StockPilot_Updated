/**
 * Inventory service (FR-8 ledger, FR-9 alerts & price history).
 */

import { api } from '@/lib/api';
import type { InventoryRow, InventoryTransaction, PriceAdjustment } from '@/types';

export interface InventoryFilters {
  category_id?: number;
  status?: string;
  stock?: 'low' | 'out' | 'ok';
  limit?: number;
  offset?: number;
}

export interface AdjustPayload {
  product_id: number;
  quantity_change: number;
  reason: string;
}

export interface PriceAdjustPayload {
  product_id: number;
  new_selling_price?: number;
  new_purchase_price?: number;
  reason: string;
}

/** FR-9.1/9.2: per-product stock with a computed condition (ok/low/out). */
export async function inventoryOverview(filters: InventoryFilters = {}): Promise<InventoryRow[]> {
  const params = new URLSearchParams();
  if (filters.category_id) params.set('category_id', String(filters.category_id));
  if (filters.status) params.set('status', filters.status);
  if (filters.stock) params.set('stock', filters.stock);
  if (filters.limit) params.set('limit', String(filters.limit));
  if (filters.offset) params.set('offset', String(filters.offset));
  const query = params.toString();
  const { data } = await api.get<InventoryRow[]>(`/inventory/overview${query ? `?${query}` : ''}`);
  return data;
}

export async function lowStock(): Promise<InventoryRow[]> {
  const { data } = await api.get<InventoryRow[]>('/inventory/low-stock');
  return data;
}

export async function outOfStock(): Promise<InventoryRow[]> {
  const { data } = await api.get<InventoryRow[]>('/inventory/out-of-stock');
  return data;
}

/** FR-8.2: the append-only movement ledger, newest first. */
export async function inventoryTransactions(
  productId?: number,
  limit = 200
): Promise<InventoryTransaction[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (productId) params.set('product_id', String(productId));
  const { data } = await api.get<InventoryTransaction[]>(`/inventory/transactions?${params}`);
  return data;
}

/** FR-8.3: manual correction (stock count, damage, write-off). */
export async function adjustStock(payload: AdjustPayload): Promise<InventoryTransaction> {
  const { data } = await api.post<InventoryTransaction>('/inventory/adjust', payload);
  return data;
}

/** FR-8.4/8.5: selling/cost price change with a mandatory reason. */
export async function adjustPrice(payload: PriceAdjustPayload): Promise<PriceAdjustment> {
  const { data } = await api.post<PriceAdjustment>('/inventory/adjust-price', payload);
  return data;
}

export async function priceAdjustments(
  productId?: number,
  limit = 100
): Promise<PriceAdjustment[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (productId) params.set('product_id', String(productId));
  const { data } = await api.get<PriceAdjustment[]>(`/inventory/price-adjustments?${params}`);
  return data;
}
