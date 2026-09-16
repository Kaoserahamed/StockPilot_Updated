/**
 * AI service (FR-30..FR-37).
 *
 * Every endpoint works without a Gemini key: the backend answers from its own
 * SQL analytics, so the UI never has to special-case a missing key.
 */

import { api } from '@/lib/api';
import type {
  AIChatResponse,
  AIInsight,
  AIRecommendation,
  AISummaryResponse,
  Anomaly,
  ForecastRow,
  ReorderRow,
} from '@/types';

export interface InsightBundle {
  preset?: string;
  insights: AIInsight[];
}

export interface ForecastBundle {
  days?: number;
  products: ForecastRow[];
}

export interface ReorderBundle {
  forecast_days: number;
  recommendations: ReorderRow[];
  needs_reorder: ReorderRow[];
}

export interface AnomalyBundle {
  anomalies: Anomaly[];
  count?: number;
}

export type SummaryKind = 'sales' | 'expenses' | 'inventory' | 'profit';

export async function chat(question: string, save = true): Promise<AIChatResponse> {
  const { data } = await api.post<AIChatResponse>('/ai/chat', { question, save });
  return data;
}

export async function insights(preset: string = 'month'): Promise<InsightBundle> {
  const { data } = await api.get<InsightBundle>(`/ai/insights?preset=${preset}`);
  return data;
}

export async function forecast(productId?: number, days = 30): Promise<ForecastBundle> {
  const params = new URLSearchParams({ days: String(days) });
  if (productId) params.set('product_id', String(productId));
  const { data } = await api.get<ForecastBundle>(`/ai/forecast?${params}`);
  return data;
}

export async function reorderRecommendations(days = 30): Promise<ReorderBundle> {
  const { data } = await api.get<ReorderBundle>(`/ai/reorder-recommendations?days=${days}`);
  return data;
}

export async function anomalies(): Promise<AnomalyBundle> {
  const { data } = await api.get<AnomalyBundle>('/ai/anomalies');
  return data;
}

export async function summarize(
  kind: SummaryKind,
  preset: string = 'month'
): Promise<AISummaryResponse> {
  const { data } = await api.post<AISummaryResponse>('/ai/summarize', { kind, preset });
  return data;
}

export async function recommendations(): Promise<AIRecommendation[]> {
  const { data } = await api.get<AIRecommendation[]>('/ai/recommendations');
  return data;
}

export async function reviewRecommendation(
  id: number,
  patch: { reviewed?: boolean; acted_upon?: boolean }
): Promise<AIRecommendation> {
  const { data } = await api.patch<AIRecommendation>(`/ai/recommendations/${id}`, patch);
  return data;
}
