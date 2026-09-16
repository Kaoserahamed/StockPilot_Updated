/**
 * Parties service (FR-6 suppliers, FR-7 customers).
 */

import { api } from '@/lib/api';
import type { Customer, Purchase, Sale, Supplier } from '@/types';

export interface SupplierPayload {
  company_name: string;
  contact_person?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
}

export interface CustomerPayload {
  name: string;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
}

export interface SupplierHistory {
  supplier_id: number;
  purchases: Purchase[];
  outstanding_balance: number;
}

export interface CustomerHistory {
  customer_id: number;
  sales: Sale[];
  outstanding_balance: number;
}

/* ------------------------------------------------------------------ suppliers */

export async function listSuppliers(): Promise<Supplier[]> {
  const { data } = await api.get<Supplier[]>('/suppliers');
  return data;
}

export async function createSupplier(payload: SupplierPayload): Promise<Supplier> {
  const { data } = await api.post<Supplier>('/suppliers', payload);
  return data;
}

export async function updateSupplier(
  id: number,
  payload: Partial<SupplierPayload>
): Promise<Supplier> {
  const { data } = await api.patch<Supplier>(`/suppliers/${id}`, payload);
  return data;
}

export async function deactivateSupplier(id: number): Promise<Supplier> {
  const { data } = await api.post<Supplier>(`/suppliers/${id}/deactivate`);
  return data;
}

/** FR-6.4/6.5: purchase history plus the outstanding payable balance. */
export async function getSupplierHistory(id: number): Promise<SupplierHistory> {
  const { data } = await api.get<SupplierHistory>(`/suppliers/${id}/purchases`);
  return data;
}

/* ------------------------------------------------------------------ customers */

export async function listCustomers(): Promise<Customer[]> {
  const { data } = await api.get<Customer[]>('/customers');
  return data;
}

export async function createCustomer(payload: CustomerPayload): Promise<Customer> {
  const { data } = await api.post<Customer>('/customers', payload);
  return data;
}

export async function updateCustomer(
  id: number,
  payload: Partial<CustomerPayload>
): Promise<Customer> {
  const { data } = await api.patch<Customer>(`/customers/${id}`, payload);
  return data;
}

/** FR-7.4: purchase history plus the outstanding receivable balance. */
export async function getCustomerHistory(id: number): Promise<CustomerHistory> {
  const { data } = await api.get<CustomerHistory>(`/customers/${id}/sales`);
  return data;
}
