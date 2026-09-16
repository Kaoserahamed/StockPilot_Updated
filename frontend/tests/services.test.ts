import { describe, expect, it, vi, beforeEach } from 'vitest';

import { api } from '../lib/api';
import * as authService from '../services/auth';
import * as catalogue from '../services/catalogue';
import * as trading from '../services/trading';
import * as finance from '../services/finance';
import * as analytics from '../services/analytics';
import * as system from '../services/system';

describe('typed service layer (over raw lib/api)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('auth service posts the documented shapes', async () => {
    const post = vi.spyOn(api, 'post');
    post.mockResolvedValueOnce({ data: { id: 1 } });
    await authService.register({ owner_name: 'O', business_name: 'B', password: 'secret123' });
    expect(post).toHaveBeenCalledWith('/auth/register', expect.anything());

    post.mockResolvedValueOnce({ data: { access_token: 'a', refresh_token: 'r' } });
    await authService.login('owner@shop.com', 'secret123');
    expect(post).toHaveBeenCalledWith('/auth/login', {
      username: 'owner@shop.com',
      password: 'secret123',
    });
  });

  it('catalogue service targets the versioned catalogue routes', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: [] });
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: { id: 1 } });
    await catalogue.listProducts({ q: 'rice' });
    expect(get).toHaveBeenCalledWith('/products?q=rice');
    await catalogue.createProduct({ name: 'Rice', sku: 'R-1' });
    expect(post).toHaveBeenCalledWith('/products', expect.anything());
  });

  it('trading service targets pos, sales, purchases and returns routes', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({ data: { id: 1 } });
    await trading.checkout({ items: [{ product_id: 1, quantity: 2 }] });
    expect(post).toHaveBeenCalledWith('/sales/checkout', expect.anything());
    await trading.cancelSale(9, 'no stock');
    expect(post).toHaveBeenCalledWith('/sales/9/cancel', expect.anything());
  });

  it('finance and system services expose typed entry points', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: {} });
    await finance.revenue({ preset: 'all' });
    expect(get).toHaveBeenCalledWith('/finance/revenue?preset=all');
    await finance.profit({ preset: 'all' });
    expect(get).toHaveBeenCalledWith('/finance/profit?preset=all');
    await analytics.dashboard({ preset: 'all' });
    expect(get).toHaveBeenCalledWith('/dashboard?preset=all');
    expect(typeof system.liveness).toBe('function');
    expect(typeof system.detailedStatus).toBe('function');
  });
});
