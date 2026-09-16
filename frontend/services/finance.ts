/**
 * Finance service (FR-15 expenses, FR-16..FR-18 revenue/COGS/profit).
 */

import { api } from '@/lib/api';
import type { CogsSummary, Expense, ProfitSummary, RevenueSummary } from '@/types';

export interface ExpensePayload {
  category: string;
  amount: number;
  description?: string | null;
  expense_date?: string;
  payment_method?: string;
}

export interface ExpenseFilters {
  category?: string;
  date_from?: string;
  date_to?: string;
}

export interface PeriodQuery {
  preset?: string;
  date_from?: string;
  date_to?: string;
}

function periodParams(query: PeriodQuery): string {
  const params = new URLSearchParams();
  if (query.preset) params.set('preset', query.preset);
  if (query.date_from) params.set('date_from', query.date_from);
  if (query.date_to) params.set('date_to', query.date_to);
  const built = params.toString();
  return built ? `?${built}` : '';
}

/* ------------------------------------------------------------------- expenses */

export async function listExpenses(filters: ExpenseFilters = {}): Promise<Expense[]> {
  const params = new URLSearchParams();
  if (filters.category) params.set('category', filters.category);
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);
  const query = params.toString();
  const { data } = await api.get<Expense[]>(`/expenses${query ? `?${query}` : ''}`);
  return data;
}

export async function createExpense(payload: ExpensePayload): Promise<Expense> {
  const { data } = await api.post<Expense>('/expenses', payload);
  return data;
}

export async function updateExpense(
  id: number,
  payload: Partial<ExpensePayload>
): Promise<Expense> {
  const { data } = await api.patch<Expense>(`/expenses/${id}`, payload);
  return data;
}

export async function deleteExpense(id: number): Promise<void> {
  await api.delete(`/expenses/${id}`);
}

/* -------------------------------------------------------------------- finance */

export async function revenue(query: PeriodQuery = {}): Promise<RevenueSummary> {
  const { data } = await api.get<RevenueSummary>(`/finance/revenue${periodParams(query)}`);
  return data;
}

export async function cogs(query: PeriodQuery = {}): Promise<CogsSummary> {
  const { data } = await api.get<CogsSummary>(`/finance/cogs${periodParams(query)}`);
  return data;
}

export async function profit(query: PeriodQuery = {}): Promise<ProfitSummary> {
  const { data } = await api.get<ProfitSummary>(`/finance/profit${periodParams(query)}`);
  return data;
}
