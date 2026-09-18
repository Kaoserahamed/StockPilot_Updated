/**
 * Contract tests for the typed service layer.
 *
 * Every function under `services/` is a thin, typed wrapper around `lib/api`
 * (`system.ts` uses the unversioned `rootApi`). These tests pin the exact URL,
 * method and payload each wrapper must emit, so a backend route rename or a
 * query-parameter regression fails here rather than inside a page no unit test
 * renders.
 *
 * Nothing touches the network: the axios instances are spied on and resolved
 * with a canned body, which is exactly what the existing service layer contract
 * promises (`const { data } = await api.get(...)`).
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api, rootApi } from '../lib/api';
import * as admin from '../services/admin';
import * as ai from '../services/ai';
import * as analytics from '../services/analytics';
import * as auth from '../services/auth';
import * as catalogue from '../services/catalogue';
import * as finance from '../services/finance';
import * as inventory from '../services/inventory';
import * as parties from '../services/parties';
import * as reports from '../services/reports';
import * as system from '../services/system';
import * as trading from '../services/trading';
import { TEST_EMAIL, TEST_PASSWORD } from './helpers';

/** Resolve every verb on the versioned client with a canned body. */
function stubApi() {
  const get = vi.spyOn(api, 'get').mockResolvedValue({ data: { ok: true } });
  const post = vi.spyOn(api, 'post').mockResolvedValue({ data: { ok: true } });
  const patch = vi.spyOn(api, 'patch').mockResolvedValue({ data: { ok: true } });
  const del = vi.spyOn(api, 'delete').mockResolvedValue({ data: null });
  return { get, post, patch, del };
}

describe('auth service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('targets the identity endpoints with the documented payloads', async () => {
    const { get, post } = stubApi();

    await auth.register({ owner_name: 'Owner', business_name: 'Shop', password: TEST_PASSWORD });
    expect(post).toHaveBeenCalledWith('/auth/register', {
      owner_name: 'Owner',
      business_name: 'Shop',
      password: TEST_PASSWORD,
    });

    await auth.login(TEST_EMAIL, TEST_PASSWORD);
    expect(post).toHaveBeenCalledWith('/auth/login', {
      username: TEST_EMAIL,
      password: TEST_PASSWORD,
    });

    await auth.logout();
    expect(post).toHaveBeenCalledWith('/auth/logout');

    await auth.refresh('refresh-token');
    expect(post).toHaveBeenCalledWith('/auth/refresh', { refresh_token: 'refresh-token' });

    await auth.forgotPassword(TEST_EMAIL);
    expect(post).toHaveBeenCalledWith('/auth/forgot-password', { username: TEST_EMAIL });

    await auth.resetPassword('reset-token', TEST_PASSWORD);
    expect(post).toHaveBeenCalledWith('/auth/reset-password', {
      token: 'reset-token',
      new_password: TEST_PASSWORD,
    });

    await auth.me();
    expect(get).toHaveBeenCalledWith('/auth/me');
  });

  it('returns the unwrapped response body', async () => {
    vi.spyOn(api, 'post').mockResolvedValue({ data: { access_token: 'a', refresh_token: 'r' } });
    await expect(auth.login(TEST_EMAIL, TEST_PASSWORD)).resolves.toEqual({
      access_token: 'a',
      refresh_token: 'r',
    });
  });
});

describe('admin service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('covers business, employee, settings and subscription routes', async () => {
    const { get, post, patch, del } = stubApi();

    await admin.getBusiness();
    expect(get).toHaveBeenCalledWith('/businesses/me');
    await admin.createBusiness({ name: 'Acme' });
    expect(post).toHaveBeenCalledWith('/businesses', { name: 'Acme' });
    await admin.updateBusiness({ name: 'Acme Ltd' });
    expect(patch).toHaveBeenCalledWith('/businesses/me', { name: 'Acme Ltd' });
    await admin.uploadLogo(new File(['logo'], 'logo.png'));
    expect(post).toHaveBeenCalledWith('/businesses/me/logo', expect.any(FormData));

    await admin.listEmployees();
    expect(get).toHaveBeenCalledWith('/employees');
    await admin.createEmployee({ name: 'Maya', role: 'Manager', password: TEST_PASSWORD });
    expect(post).toHaveBeenCalledWith('/employees', expect.anything());
    await admin.updateEmployeeRole(3, 'Cashier');
    expect(patch).toHaveBeenCalledWith('/employees/3/role', { role: 'Cashier' });
    await admin.deactivateEmployee(3);
    expect(post).toHaveBeenCalledWith('/employees/3/deactivate');
    await admin.activateEmployee(3);
    expect(post).toHaveBeenCalledWith('/employees/3/activate');
    await admin.resetEmployeePassword(3, TEST_PASSWORD);
    expect(post).toHaveBeenCalledWith('/employees/3/reset-password', {
      new_password: TEST_PASSWORD,
    });
    await admin.removeEmployee(3);
    expect(del).toHaveBeenCalledWith('/employees/3');

    await admin.getSettings();
    expect(get).toHaveBeenCalledWith('/settings');
    await admin.updateSettings({ currency: 'BDT' });
    expect(patch).toHaveBeenCalledWith('/settings', { currency: 'BDT' });
    await admin.getSubscription();
    expect(get).toHaveBeenCalledWith('/subscription');
    await admin.changePlan('pro');
    expect(patch).toHaveBeenCalledWith('/subscription', { plan: 'pro' });
  });

  it('builds the audit-log query from whatever filters it is given', async () => {
    const { get } = stubApi();

    await admin.listAuditLogs();
    expect(get).toHaveBeenCalledWith('/audit-logs');

    await admin.listAuditLogs({ action: 'create', resource: 'product', limit: 25 });
    expect(get).toHaveBeenCalledWith('/audit-logs?action=create&resource=product&limit=25');
  });
});

describe('catalogue service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('covers category and product routes', async () => {
    const { get, post, patch, del } = stubApi();

    await catalogue.listCategories();
    expect(get).toHaveBeenCalledWith('/categories');
    await catalogue.createCategory({ name: 'Grains' });
    expect(post).toHaveBeenCalledWith('/categories', { name: 'Grains' });
    await catalogue.updateCategory(4, { name: 'Grains & Rice' });
    expect(patch).toHaveBeenCalledWith('/categories/4', { name: 'Grains & Rice' });
    await catalogue.deactivateCategory(4);
    expect(post).toHaveBeenCalledWith('/categories/4/deactivate');
    await catalogue.deleteCategory(4);
    expect(del).toHaveBeenCalledWith('/categories/4');

    await catalogue.getProduct(7);
    expect(get).toHaveBeenCalledWith('/products/7');
    await catalogue.createProduct({ name: 'Rice', sku: 'R-1' });
    expect(post).toHaveBeenCalledWith('/products', { name: 'Rice', sku: 'R-1' });
    await catalogue.updateProduct(7, { selling_price: 120 });
    expect(patch).toHaveBeenCalledWith('/products/7', { selling_price: 120 });
    await catalogue.deactivateProduct(7);
    expect(post).toHaveBeenCalledWith('/products/7/deactivate');
    await catalogue.activateProduct(7);
    expect(post).toHaveBeenCalledWith('/products/7/activate');
    await catalogue.uploadProductImage(7, new File(['img'], 'rice.png'));
    expect(post).toHaveBeenCalledWith('/products/7/image', expect.any(FormData));
  });

  it('omits absent product filters and serialises the ones it is given', async () => {
    const { get } = stubApi();

    await catalogue.listProducts();
    expect(get).toHaveBeenCalledWith('/products');

    await catalogue.listProducts({
      q: 'rice',
      category_id: 4,
      brand: 'Acme',
      low_stock: true,
      out_of_stock: true,
      limit: 20,
      offset: 40,
    });
    expect(get).toHaveBeenCalledWith(
      '/products?q=rice&category_id=4&brand=Acme&low_stock=true&out_of_stock=true&limit=20&offset=40'
    );
  });
});

describe('parties service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('covers supplier and customer routes', async () => {
    const { get, post, patch } = stubApi();

    await parties.listSuppliers();
    expect(get).toHaveBeenCalledWith('/suppliers');
    await parties.createSupplier({ company_name: 'Acme Supply' });
    expect(post).toHaveBeenCalledWith('/suppliers', { company_name: 'Acme Supply' });
    await parties.updateSupplier(5, { phone: '01700000000' });
    expect(patch).toHaveBeenCalledWith('/suppliers/5', { phone: '01700000000' });
    await parties.deactivateSupplier(5);
    expect(post).toHaveBeenCalledWith('/suppliers/5/deactivate');
    await parties.getSupplierHistory(5);
    expect(get).toHaveBeenCalledWith('/suppliers/5/purchases');

    await parties.listCustomers();
    expect(get).toHaveBeenCalledWith('/customers');
    await parties.createCustomer({ name: 'Walk-in' });
    expect(post).toHaveBeenCalledWith('/customers', { name: 'Walk-in' });
    await parties.updateCustomer(6, { email: 'walk-in@shop.test' });
    expect(patch).toHaveBeenCalledWith('/customers/6', { email: 'walk-in@shop.test' });
    await parties.getCustomerHistory(6);
    expect(get).toHaveBeenCalledWith('/customers/6/sales');
  });
});

describe('inventory service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('covers the ledger, alerts and price-history routes', async () => {
    const { get, post } = stubApi();

    await inventory.lowStock();
    expect(get).toHaveBeenCalledWith('/inventory/low-stock');
    await inventory.outOfStock();
    expect(get).toHaveBeenCalledWith('/inventory/out-of-stock');
    await inventory.adjustStock({ product_id: 1, quantity_change: -2, reason: 'damage' });
    expect(post).toHaveBeenCalledWith('/inventory/adjust', expect.anything());
    await inventory.adjustPrice({ product_id: 1, new_selling_price: 90, reason: 'promo' });
    expect(post).toHaveBeenCalledWith('/inventory/adjust-price', expect.anything());
  });

  it('builds the overview, transaction and price-adjustment queries', async () => {
    const { get } = stubApi();

    await inventory.inventoryOverview();
    expect(get).toHaveBeenCalledWith('/inventory/overview');

    await inventory.inventoryOverview({
      category_id: 4,
      status: 'active',
      stock: 'low',
      limit: 10,
      offset: 20,
    });
    expect(get).toHaveBeenCalledWith(
      '/inventory/overview?category_id=4&status=active&stock=low&limit=10&offset=20'
    );

    await inventory.inventoryTransactions();
    expect(get).toHaveBeenCalledWith('/inventory/transactions?limit=200');
    await inventory.inventoryTransactions(9, 5);
    expect(get).toHaveBeenCalledWith('/inventory/transactions?limit=5&product_id=9');

    await inventory.priceAdjustments();
    expect(get).toHaveBeenCalledWith('/inventory/price-adjustments?limit=100');
    await inventory.priceAdjustments(9, 3);
    expect(get).toHaveBeenCalledWith('/inventory/price-adjustments?limit=3&product_id=9');
  });
});

describe('trading service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('covers purchasing, POS, sales, returns and invoices', async () => {
    const { get, post } = stubApi();

    await trading.listPurchases();
    expect(get).toHaveBeenCalledWith('/purchases');
    await trading.getPurchase(11);
    expect(get).toHaveBeenCalledWith('/purchases/11');
    await trading.createPurchase({
      supplier_id: 5,
      items: [{ product_id: 1, quantity: 4, unit_cost: 60 }],
    });
    expect(post).toHaveBeenCalledWith('/purchases', expect.anything());
    await trading.payPurchase(11, 120);
    expect(post).toHaveBeenCalledWith('/purchases/11/pay', { amount: 120 });
    await trading.cancelPurchase(11);
    expect(post).toHaveBeenCalledWith('/purchases/11/cancel');

    await trading.posSearch('rice & oil');
    expect(get).toHaveBeenCalledWith('/pos/search?q=rice%20%26%20oil');
    await trading.checkout({ items: [{ product_id: 1, quantity: 2 }] });
    expect(post).toHaveBeenCalledWith('/sales/checkout', expect.anything());
    await trading.listSales();
    expect(get).toHaveBeenCalledWith('/sales');
    await trading.getSale(12);
    expect(get).toHaveBeenCalledWith('/sales/12');
    await trading.cancelSale(12, 'customer changed mind');
    expect(post).toHaveBeenCalledWith('/sales/12/cancel', { reason: 'customer changed mind' });

    await trading.listReturns();
    expect(get).toHaveBeenCalledWith('/returns');
    await trading.createReturn({
      sale_id: 12,
      reason: 'damaged',
      items: [{ sale_item_id: 1, quantity: 1 }],
    });
    expect(post).toHaveBeenCalledWith('/returns', expect.anything());

    await trading.getInvoice(12);
    expect(get).toHaveBeenCalledWith('/invoices/12');
    expect(trading.invoicePdfUrl(12)).toBe('/invoices/12/pdf');
  });
});

describe('finance service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('covers expenses and the revenue/COGS/profit summaries', async () => {
    const { get, post, patch, del } = stubApi();

    await finance.listExpenses();
    expect(get).toHaveBeenCalledWith('/expenses');
    await finance.listExpenses({
      category: 'rent',
      date_from: '2026-01-01',
      date_to: '2026-01-31',
    });
    expect(get).toHaveBeenCalledWith(
      '/expenses?category=rent&date_from=2026-01-01&date_to=2026-01-31'
    );
    await finance.createExpense({ category: 'rent', amount: 500 });
    expect(post).toHaveBeenCalledWith('/expenses', { category: 'rent', amount: 500 });
    await finance.updateExpense(2, { amount: 600 });
    expect(patch).toHaveBeenCalledWith('/expenses/2', { amount: 600 });
    await finance.deleteExpense(2);
    expect(del).toHaveBeenCalledWith('/expenses/2');

    await finance.revenue();
    expect(get).toHaveBeenCalledWith('/finance/revenue');
    await finance.revenue({ preset: 'month' });
    expect(get).toHaveBeenCalledWith('/finance/revenue?preset=month');
    await finance.cogs({ date_from: '2026-01-01' });
    expect(get).toHaveBeenCalledWith('/finance/cogs?date_from=2026-01-01');
    await finance.profit({ preset: 'year', date_to: '2026-12-31' });
    expect(get).toHaveBeenCalledWith('/finance/profit?preset=year&date_to=2026-12-31');
  });
});

describe('analytics service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('covers the dashboard and the performance endpoints', async () => {
    const { get } = stubApi();

    await analytics.dashboard();
    expect(get).toHaveBeenCalledWith('/dashboard');
    await analytics.dashboard({ preset: 'all', limit: 5 });
    expect(get).toHaveBeenCalledWith('/dashboard?preset=all&limit=5');
    await analytics.productAnalytics({ date_from: '2026-01-01' });
    expect(get).toHaveBeenCalledWith('/analytics/products?date_from=2026-01-01');
    await analytics.customerAnalytics({ date_to: '2026-02-01' });
    expect(get).toHaveBeenCalledWith('/analytics/customers?date_to=2026-02-01');
    await analytics.supplierAnalytics({ preset: 'week' });
    expect(get).toHaveBeenCalledWith('/analytics/suppliers?preset=week');
  });
});

describe('ai service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('covers chat, insights, forecasting and the review workflow', async () => {
    const { get, post, patch } = stubApi();

    await ai.chat('how are sales?');
    expect(post).toHaveBeenCalledWith('/ai/chat', { question: 'how are sales?', save: true });
    await ai.chat('and profit?', false);
    expect(post).toHaveBeenCalledWith('/ai/chat', { question: 'and profit?', save: false });

    await ai.insights();
    expect(get).toHaveBeenCalledWith('/ai/insights?preset=month');
    await ai.insights('week');
    expect(get).toHaveBeenCalledWith('/ai/insights?preset=week');

    await ai.forecast();
    expect(get).toHaveBeenCalledWith('/ai/forecast?days=30');
    await ai.forecast(7, 14);
    expect(get).toHaveBeenCalledWith('/ai/forecast?days=14&product_id=7');

    await ai.reorderRecommendations();
    expect(get).toHaveBeenCalledWith('/ai/reorder-recommendations?days=30');
    await ai.reorderRecommendations(7);
    expect(get).toHaveBeenCalledWith('/ai/reorder-recommendations?days=7');

    await ai.anomalies();
    expect(get).toHaveBeenCalledWith('/ai/anomalies');

    await ai.summarize('sales');
    expect(post).toHaveBeenCalledWith('/ai/summarize', { kind: 'sales', preset: 'month' });
    await ai.summarize('profit', 'year');
    expect(post).toHaveBeenCalledWith('/ai/summarize', { kind: 'profit', preset: 'year' });

    await ai.recommendations();
    expect(get).toHaveBeenCalledWith('/ai/recommendations');
    await ai.reviewRecommendation(3, { reviewed: true, acted_upon: false });
    expect(patch).toHaveBeenCalledWith('/ai/recommendations/3', {
      reviewed: true,
      acted_upon: false,
    });
  });
});

describe('reports service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('covers the JSON report table and the export paths', async () => {
    const { get } = stubApi();

    await reports.report('sales');
    expect(get).toHaveBeenCalledWith('/reports/sales?format=json');
    await reports.report('profit', { preset: 'all', limit: 10 });
    expect(get).toHaveBeenCalledWith('/reports/profit?format=json&preset=all&limit=10');

    expect(reports.reportExportPath('inventory', 'csv', { preset: 'month' })).toBe(
      '/reports/inventory?format=csv&preset=month'
    );
    expect(reports.reportExportPath('expenses', 'xlsx', { date_from: '2026-01-01' })).toBe(
      '/reports/expenses?format=xlsx&date_from=2026-01-01'
    );
    expect(reports.profitPdfPath()).toBe('/reports/profit/pdf?preset=month');
    expect(reports.profitPdfPath('year')).toBe('/reports/profit/pdf?preset=year');
  });
});

describe('system service and the services barrel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('probes the unversioned health endpoints through rootApi', async () => {
    const get = vi.spyOn(rootApi, 'get').mockResolvedValue({ data: { status: 'ok' } });

    await expect(system.liveness()).resolves.toEqual({ status: 'ok' });
    expect(get).toHaveBeenCalledWith('/health');

    await system.detailedStatus();
    expect(get).toHaveBeenCalledWith('/health/detailed');
  });

  it('re-exports every service module through the barrel', async () => {
    const barrel = await import('../services');
    expect(Object.keys(barrel)).toEqual(
      expect.arrayContaining([
        'admin',
        'ai',
        'analytics',
        'auth',
        'catalogue',
        'finance',
        'inventory',
        'parties',
        'reports',
        'system',
        'trading',
      ])
    );
    expect(barrel.trading.invoicePdfUrl(1)).toBe('/invoices/1/pdf');
  });
});
