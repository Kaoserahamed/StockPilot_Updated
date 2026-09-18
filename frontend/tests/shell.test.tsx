/**
 * Render tests for the application shell: sidebar navigation, tenant header,
 * identity block and the sign-out affordance.
 *
 * `next/navigation` is mocked (there is no router in this environment) and
 * `lib/auth` is mocked so each test can pick the signed-in identity; the tenant
 * query is served by spying on `lib/api`.
 */

import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Shell } from '../components/Shell';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { AuthUser } from '../types';

const { pathnameRef } = vi.hoisted(() => ({ pathnameRef: { current: '/dashboard' } }));

vi.mock('next/navigation', () => ({ usePathname: () => pathnameRef.current }));
vi.mock('../lib/auth', () => ({ useAuth: vi.fn() }));

const owner: AuthUser = {
  id: 1,
  name: 'Maya',
  email: 'maya@shop.test',
  phone: null,
  is_active: true,
};

const logout = vi.fn();

/** Point the mocked `useAuth` at a signed-in user (or nobody). */
function signedIn(as: AuthUser | null = owner): void {
  vi.mocked(useAuth).mockReturnValue({
    user: as,
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout,
    refresh: vi.fn(),
  });
}

function renderShell() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <Shell>
        <p>page body</p>
      </Shell>
    </QueryClientProvider>
  );
}

describe('Shell', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    logout.mockReset();
    pathnameRef.current = '/dashboard';
    signedIn();
  });

  it('renders every navigation group with the tenant and identity blocks', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { name: 'Acme Store' } });
    renderShell();

    await screen.findAllByText('Acme Store');
    for (const group of ['Sell', 'Manage', 'Grow', 'Workspace']) {
      expect(screen.getAllByText(group).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByText('Maya').length).toBeGreaterThan(0);
    expect(screen.getByText('maya@shop.test')).toBeDefined();
    expect(screen.getByText('page body')).toBeDefined();
    // Every route in the map is reachable from the sidebar.
    for (const href of ['/pos', '/sales', '/purchases', '/inventory', '/reports', '/settings']) {
      expect(document.querySelector(`a[href="${href}"]`)).toBeTruthy();
    }
  });

  it('marks the active route, including nested paths', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { name: 'Acme Store' } });
    pathnameRef.current = '/products/42';
    renderShell();
    await screen.findAllByText('Acme Store');

    expect(document.querySelector('a[href="/products"]')?.className).toContain('bg-emerald-500/15');
    expect(document.querySelector('a[href="/dashboard"]')?.className).not.toContain(
      'bg-emerald-500/15'
    );
  });

  it('falls back to generic labels without a session or business name', async () => {
    signedIn(null);
    vi.spyOn(api, 'get').mockResolvedValue({ data: {} });
    renderShell();

    expect(screen.getByText('Your business')).toBeDefined();
    expect(screen.getByText('Account')).toBeDefined();
    // "Workspace" is both a group title and the header fallback.
    expect(screen.getAllByText('Workspace').length).toBeGreaterThanOrEqual(2);
  });

  it('signs out through the auth context', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ data: { name: 'Acme Store' } });
    renderShell();
    await screen.findAllByText('Acme Store');

    fireEvent.click(screen.getByText('Sign out'));
    expect(logout).toHaveBeenCalledTimes(1);
  });
});
