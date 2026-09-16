/**
 * Catalogue service (FR-4 categories, FR-5 products).
 */

import { api } from '@/lib/api';
import type { Category, Product } from '@/types';

export interface CategoryPayload {
  name: string;
  description?: string;
}

export interface ProductPayload {
  name: string;
  sku: string;
  barcode?: string | null;
  category_id?: number | null;
  brand?: string | null;
  unit?: string;
  purchase_price?: number;
  selling_price?: number;
  min_stock?: number;
}

export interface ProductFilters {
  q?: string;
  category_id?: number;
  brand?: string;
  low_stock?: boolean;
  out_of_stock?: boolean;
  limit?: number;
  offset?: number;
}

/* ---------------------------------------------------------------- categories */

export async function listCategories(): Promise<Category[]> {
  const { data } = await api.get<Category[]>('/categories');
  return data;
}

export async function createCategory(payload: CategoryPayload): Promise<Category> {
  const { data } = await api.post<Category>('/categories', payload);
  return data;
}

export async function updateCategory(
  id: number,
  payload: Partial<CategoryPayload>
): Promise<Category> {
  const { data } = await api.patch<Category>(`/categories/${id}`, payload);
  return data;
}

export async function deactivateCategory(id: number): Promise<Category> {
  const { data } = await api.post<Category>(`/categories/${id}/deactivate`);
  return data;
}

export async function deleteCategory(id: number): Promise<void> {
  await api.delete(`/categories/${id}`);
}

/* ------------------------------------------------------------------ products */

export async function listProducts(filters: ProductFilters = {}): Promise<Product[]> {
  const params = new URLSearchParams();
  if (filters.q) params.set('q', filters.q);
  if (filters.category_id) params.set('category_id', String(filters.category_id));
  if (filters.brand) params.set('brand', filters.brand);
  if (filters.low_stock) params.set('low_stock', 'true');
  if (filters.out_of_stock) params.set('out_of_stock', 'true');
  if (filters.limit) params.set('limit', String(filters.limit));
  if (filters.offset) params.set('offset', String(filters.offset));
  const query = params.toString();
  const { data } = await api.get<Product[]>(`/products${query ? `?${query}` : ''}`);
  return data;
}

export async function getProduct(id: number): Promise<Product> {
  const { data } = await api.get<Product>(`/products/${id}`);
  return data;
}

export async function createProduct(payload: ProductPayload): Promise<Product> {
  const { data } = await api.post<Product>('/products', payload);
  return data;
}

export async function updateProduct(
  id: number,
  payload: Partial<ProductPayload>
): Promise<Product> {
  const { data } = await api.patch<Product>(`/products/${id}`, payload);
  return data;
}

export async function deactivateProduct(id: number): Promise<Product> {
  const { data } = await api.post<Product>(`/products/${id}/deactivate`);
  return data;
}

export async function activateProduct(id: number): Promise<Product> {
  const { data } = await api.post<Product>(`/products/${id}/activate`);
  return data;
}

/** FR-5.6: upload a product image (multipart, handled by the API as form data). */
export async function uploadProductImage(id: number, file: File): Promise<Product> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<Product>(`/products/${id}/image`, form);
  return data;
}
