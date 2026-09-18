/**
 * Shared domain types for the StockPilot client.
 *
 * These mirror the Pydantic contracts in `backend/app/schemas/schemas.py` and
 * are the single source of truth for `services/` (the only fetch layer) and
 * for page components. No runtime code lives in this directory - see
 * `docs/architecture/system-architecture.md`.
 */

/* ------------------------------------------------------------------ identity */

export interface AuthUser {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Business {
  id: number;
  name: string;
  address: string | null;
  phone: string | null;
  email: string | null;
  currency: string;
  tax_rate: number;
  invoice_format?: string;
  min_stock_default?: number;
  logo_path?: string | null;
}

export interface BusinessSettings {
  currency: string;
  tax_rate: number;
  invoice_format: string;
  min_stock_default: number;
  business_name: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
}

export type Role = 'Owner' | 'Manager' | 'Cashier';

export interface Employee {
  membership_id: number;
  user: AuthUser;
  role: Role;
  is_active: boolean;
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  action: string;
  resource: string;
  resource_id: string | null;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

export interface Subscription {
  plan: 'free' | 'basic' | 'pro';
  status: string;
  product_limit: number;
  employee_limit: number;
  product_count: number;
  employee_count: number;
  product_usage_pct: number;
  employee_usage_pct: number;
  near_limit: boolean;
  at_limit: boolean;
  message: string | null;
}

/* ----------------------------------------------------------------- catalogue */

export interface Category {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface Product {
  id: number;
  name: string;
  sku: string;
  barcode: string | null;
  category_id: number | null;
  brand: string | null;
  unit: string;
  purchase_price: number;
  selling_price: number;
  min_stock: number;
  quantity_on_hand: number;
  is_active: boolean;
  image_path?: string | null;
}

/* -------------------------------------------------------------------- parties */

export interface Supplier {
  id: number;
  company_name: string;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  is_active: boolean;
  outstanding_balance: number;
}

export interface Customer {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  is_active: boolean;
  outstanding_balance: number;
}

/* ------------------------------------------------------------------ inventory */

export interface InventoryRow {
  id: number;
  name: string;
  sku: string;
  category_id: number | null;
  quantity: number;
  min_stock: number;
  condition: 'ok' | 'low' | 'out';
  is_active: boolean;
  selling_price: number;
  purchase_price: number;
}

export interface InventoryTransaction {
  id: number;
  product_id: number;
  quantity_change: number;
  tx_type: string;
  reason: string | null;
  user_id: number | null;
  related_id: string | null;
  created_at: string;
}

export interface PriceAdjustment {
  id: number;
  product_id: number;
  old_selling_price: number;
  new_selling_price: number;
  old_purchase_price: number;
  new_purchase_price: number;
  reason: string;
  user_id: number | null;
  created_at: string;
}

/* ------------------------------------------------------------------- trading */

export interface PurchaseItem {
  id: number;
  product_id: number;
  product_name: string | null;
  quantity: number;
  unit_cost: number;
  line_total: number;
}

export interface Purchase {
  id: number;
  supplier_id: number;
  supplier_name: string | null;
  purchase_date: string;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  payment_status: PaymentStatus;
  status: string;
  note: string | null;
  items: PurchaseItem[];
}

export type PaymentStatus = 'paid' | 'partial' | 'unpaid';

export interface SaleItem {
  id: number;
  product_id: number;
  product_name: string | null;
  quantity: number;
  unit_price: number;
  discount: number;
  line_total: number;
  returned_qty: number;
}

export interface Sale {
  id: number;
  invoice_no: string;
  customer_id: number | null;
  customer_name: string | null;
  subtotal: number;
  discount_amount: number;
  tax_percent: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  payment_method: string;
  payment_status: PaymentStatus;
  refunded_amount?: number;
  status: string;
  created_at: string;
  items: SaleItem[];
}

export interface ReturnRecord {
  id: number;
  sale_id: number;
  reason: string;
  refund_amount: number;
  created_at: string;
}

export interface Expense {
  id: number;
  category: string;
  amount: number;
  description: string | null;
  expense_date: string;
  payment_method: string;
}

/* ------------------------------------------------------------------- finance */

export interface TrendBucket {
  period: string;
  orders: number;
  revenue: number;
}

export interface RevenueSummary {
  gross_revenue: number;
  net_revenue: number;
  refunded: number;
  trend: TrendBucket[];
  preset: string;
}

export interface CogsSummary {
  cogs: number;
  per_product?: { product_id: number; product_name: string | null; cost: number }[];
}

export interface ProfitSummary {
  gross_revenue: number;
  refunded: number;
  net_revenue: number;
  cogs: number;
  gross_profit: number;
  total_expenses: number;
  net_profit: number;
  orders: number;
}

export interface ProductPerformance {
  product_id: number;
  product_name: string | null;
  quantity: number;
  revenue: number;
  profit: number;
}

export interface CustomerStat {
  customer_id: number | null;
  customer_name: string | null;
  orders: number;
  spent: number;
}

export interface SupplierStat {
  supplier_id: number;
  supplier_name: string | null;
  orders: number;
  purchased: number;
  outstanding: number;
}

export interface InventoryValue {
  units: number;
  skus: number;
  cost_value: number;
  retail_value: number;
}

export interface Dashboard {
  preset: string;
  total_sales: number;
  orders: number;
  revenue: number;
  gross_profit: number;
  net_profit: number;
  expenses: number;
  cogs: number;
  inventory: InventoryValue;
  low_stock_count: number;
  out_of_stock_count: number;
  sales_trend: TrendBucket[];
  top_products: ProductPerformance[];
}

export interface ReportTable {
  rows: Record<string, unknown>[];
  summary: Record<string, unknown> | (Record<string, unknown>[] & { orders?: number });
}

/* ------------------------------------------------------------------ reporting */

export type ReportKind = 'sales' | 'inventory' | 'purchases' | 'expenses' | 'profit';
export type ExportFormat = 'json' | 'csv' | 'xlsx' | 'pdf';
export type Preset = 'today' | 'week' | 'month' | 'year' | 'all' | 'custom';

/* -------------------------------------------------------------------------- ai */

export interface AIInsight {
  type: string;
  title: string;
  detail: string;
  z?: number;
  period?: string;
}

export interface AIRecommendation {
  id: number;
  kind: string;
  title: string;
  body: string;
  reviewed: boolean;
  acted_upon: boolean;
  created_at: string;
}

export interface AIChatResponse {
  answer: string;
  data: Record<string, unknown>;
  recommendation_id: number | null;
}

export interface AISummaryResponse {
  kind: string;
  summary: string;
  recommendation_id: number | null;
}

export interface ForecastRow {
  product_id: number;
  product_name: string | null;
  predicted_demand: number;
}

export interface ReorderRow extends ForecastRow {
  min_stock: number;
  recommended_qty: number;
  needs_reorder: boolean;
  reason: string;
}

export interface Anomaly {
  type: string;
  title: string;
  detail: string;
  z?: number;
  period?: string;
}
