/**
 * Browser session storage helpers.
 *
 * Single place that knows the storage keys, so the axios interceptor, the auth
 * context and the logout flow can never drift apart.
 */

const TOKEN_KEY = 'pos_token';
const BUSINESS_KEY = 'pos_business_id';

const isBrowser = () => typeof window !== 'undefined';

export function getToken(): string | null {
  return isBrowser() ? localStorage.getItem(TOKEN_KEY) : null;
}

export function setToken(token: string | null): void {
  if (!isBrowser()) return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

/** Multi-tenant switch: sent as `X-Business-Id` on every request. */
export function getBusinessId(): string | null {
  return isBrowser() ? localStorage.getItem(BUSINESS_KEY) : null;
}

export function setBusinessId(businessId: number | string | null): void {
  if (!isBrowser()) return;
  if (businessId === null) localStorage.removeItem(BUSINESS_KEY);
  else localStorage.setItem(BUSINESS_KEY, String(businessId));
}

export function clearSession(): void {
  if (!isBrowser()) return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(BUSINESS_KEY);
}
