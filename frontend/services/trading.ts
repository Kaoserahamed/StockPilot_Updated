/**
 * Trading service: purchasing (FR-10), POS & sales (FR-11..FR-13) and
 * returns (FR-14).
 */

import { api } from '@/lib/api';
import type { Product, Purchase, ReturnRecord, Sale } from '@/types';

export interface PurchaseItemInput {
  product_id: number;
  quantity: number;
  unit_cost: number;
}

export interface PurchasePayload {
  supplier_id: number;
  items: PurchaseItemInput[];
  discount_amount?: number;
  tax_amount?: number;
  paid_amount?: number;
  note?: string | null;
}

export interface CartItemInput {
  product_id: number;
  quantity: number;
  unit_price?: number;
  discount?: number;
}

export interface CheckoutPayload {
  items: CartItemInput[];
  customer_id?: number | null;
  discount_amount?: number;
  tax_percent?: number;
  paid_amount?: number | null;
  payment_method?: string;
}

export interface ReturnPayload {
  sale_id: number;
  reason: string;
  items: { sale_item_id: number; quantity: number }[];
}

/* ----------------------------------------------------------------- purchases */

export async function listPurchases(): Promise<Purchase[]> {
  const { data } = await api.get<Purchase[]>('/purchases');
  return data;
}

export async function getPurchase(id: number): Promise<Purchase> {
  const { data } = await api.get<Purchase>(`/purchases/${id}`);
  return data;
}

export async function createPurchase(payload: PurchasePayload): Promise<Purchase> {
  const { data } = await api.post<Purchase>('/purchases', payload);
  return data;
}

export async function payPurchase(id: number, amount: number): Promise<Purchase> {
  const { data } = await api.post<Purchase>(`/purchases/${id}/pay`, { amount });
  return data;
}

export async function cancelPurchase(id: number): Promise<Purchase> {
  const { data } = await api.post<Purchase>(`/purchases/${id}/cancel`);
  return data;
}

/* --------------------------------------------------------------------- sales */

/** FR-11.2: barcode/name lookup for the POS grid (active products only). */
export async function posSearch(term: string): Promise<Product[]> {
  const { data } = await api.get<Product[]>(`/pos/search?q=${encodeURIComponent(term)}`);
  return data;
}

export async function checkout(payload: CheckoutPayload): Promise<Sale> {
  const { data } = await api.post<Sale>('/sales/checkout', payload);
  return data;
}

export async function listSales(): Promise<Sale[]> {
  const { data } = await api.get<Sale[]>('/sales');
  return data;
}

export async function getSale(id: number): Promise<Sale> {
  const { data } = await api.get<Sale>(`/sales/${id}`);
  return data;
}

export async function cancelSale(id: number, reason: string): Promise<Sale> {
  const { data } = await api.post<Sale>(`/sales/${id}/cancel`, { reason });
  return data;
}

/* ------------------------------------------------------------------- returns */

export async function listReturns(): Promise<ReturnRecord[]> {
  const { data } = await api.get<ReturnRecord[]>('/returns');
  return data;
}

export async function createReturn(payload: ReturnPayload): Promise<ReturnRecord> {
  const { data } = await api.post<ReturnRecord>('/returns', payload);
  return data;
}

/** FR-13.3/13.4: invoice payload for the on-screen view. */
export async function getInvoice(saleId: number): Promise<Sale> {
  const { data } = await api.get<Sale>(`/invoices/${saleId}`);
  return data;
}

/** FR-13.4: invoice as a downloadable PDF. */
export function invoicePdfUrl(saleId: number): string {
  return `/invoices/${saleId}/pdf`;
}
