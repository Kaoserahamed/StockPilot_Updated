/**
 * Administration service: business profile (FR-2), employees & roles (FR-3),
 * settings (FR-28), subscription (FR-29) and the audit trail (FR-27).
 */

import { api } from '@/lib/api';
import type { AuditLog, Business, BusinessSettings, Employee, Role, Subscription } from '@/types';

export interface EmployeePayload {
  name: string;
  role: Role;
  password: string;
  email?: string | null;
  phone?: string | null;
}

export interface SettingsPayload {
  currency?: string;
  tax_rate?: number;
  invoice_format?: string;
  min_stock_default?: number;
  business_name?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
}

/* ------------------------------------------------------------------ business */

export async function getBusiness(): Promise<Business> {
  const { data } = await api.get<Business>('/businesses/me');
  return data;
}

export async function createBusiness(payload: {
  name: string;
  currency?: string;
  tax_rate?: number;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
}): Promise<Business> {
  const { data } = await api.post<Business>('/businesses', payload);
  return data;
}

export async function updateBusiness(payload: Partial<Business>): Promise<Business> {
  const { data } = await api.patch<Business>('/businesses/me', payload);
  return data;
}

/** FR-2.2: logo upload (multipart form data). */
export async function uploadLogo(file: File): Promise<Business> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<Business>('/businesses/me/logo', form);
  return data;
}

/* ----------------------------------------------------------------- employees */

export async function listEmployees(): Promise<Employee[]> {
  const { data } = await api.get<Employee[]>('/employees');
  return data;
}

export async function createEmployee(payload: EmployeePayload): Promise<Employee> {
  const { data } = await api.post<Employee>('/employees', payload);
  return data;
}

export async function updateEmployeeRole(membershipId: number, role: Role): Promise<Employee> {
  const { data } = await api.patch<Employee>(`/employees/${membershipId}/role`, { role });
  return data;
}

export async function deactivateEmployee(membershipId: number): Promise<Employee> {
  const { data } = await api.post<Employee>(`/employees/${membershipId}/deactivate`);
  return data;
}

export async function activateEmployee(membershipId: number): Promise<Employee> {
  const { data } = await api.post<Employee>(`/employees/${membershipId}/activate`);
  return data;
}

export async function resetEmployeePassword(
  membershipId: number,
  newPassword: string
): Promise<Employee> {
  const { data } = await api.post<Employee>(`/employees/${membershipId}/reset-password`, {
    new_password: newPassword,
  });
  return data;
}

export async function removeEmployee(membershipId: number): Promise<void> {
  await api.delete(`/employees/${membershipId}`);
}

/* ------------------------------------------------------------------ settings */

export async function getSettings(): Promise<BusinessSettings> {
  const { data } = await api.get<BusinessSettings>('/settings');
  return data;
}

export async function updateSettings(payload: SettingsPayload): Promise<BusinessSettings> {
  const { data } = await api.patch<BusinessSettings>('/settings', payload);
  return data;
}

/* -------------------------------------------------------------- subscription */

export async function getSubscription(): Promise<Subscription> {
  const { data } = await api.get<Subscription>('/subscription');
  return data;
}

export async function changePlan(plan: Subscription['plan']): Promise<Subscription> {
  const { data } = await api.patch<Subscription>('/subscription', { plan });
  return data;
}

/* --------------------------------------------------------------- audit trail */

export interface AuditFilters {
  action?: string;
  resource?: string;
  limit?: number;
}

export async function listAuditLogs(filters: AuditFilters = {}): Promise<AuditLog[]> {
  const params = new URLSearchParams();
  if (filters.action) params.set('action', filters.action);
  if (filters.resource) params.set('resource', filters.resource);
  if (filters.limit) params.set('limit', String(filters.limit));
  const query = params.toString();
  const { data } = await api.get<AuditLog[]>(`/audit-logs${query ? `?${query}` : ''}`);
  return data;
}
