import { describe, expect, it } from 'vitest';

import { reportExportPath } from '../services/reports';

describe('page smoke contracts (auth, POS, products, inventory)', () => {
  it('auth pages post to the identity routes', async () => {
    const login = await import('../app/login/page');
    const register = await import('../app/register/page');
    expect(typeof login.default).toBe('function');
    expect(typeof register.default).toBe('function');
  });

  it('pos, products and inventory pages exist as route components', async () => {
    const pos = await import('../app/pos/page');
    const products = await import('../app/products/page');
    const inventory = await import('../app/inventory/page');
    expect(typeof pos.default).toBe('function');
    expect(typeof products.default).toBe('function');
    expect(typeof inventory.default).toBe('function');
  });

  it('report export paths cover every downloadable kind', () => {
    for (const kind of ['sales', 'inventory', 'purchases', 'expenses', 'profit'] as const) {
      expect(reportExportPath(kind, 'csv', { preset: 'all' })).toContain(`/reports/${kind}`);
      expect(reportExportPath(kind, 'pdf', { preset: 'all' })).toContain('format=pdf');
    }
  });

  it('service layer exposes the trading and inventory entry points', async () => {
    const trading = await import('../services/trading');
    const inventory = await import('../services/inventory');
    const catalogue = await import('../services/catalogue');
    expect(typeof trading.checkout).toBe('function');
    expect(typeof trading.posSearch).toBe('function');
    expect(typeof inventory.adjustStock).toBe('function');
    expect(typeof catalogue.listProducts).toBe('function');
  });
});
