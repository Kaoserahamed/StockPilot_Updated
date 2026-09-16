import { describe, expect, it } from 'vitest';

import { getBusinessId, getToken, setBusinessId, setToken, clearSession } from '../lib/session';

describe('browser session storage', () => {
  it('round-trips the bearer token', () => {
    setToken('tok-123');
    expect(getToken()).toBe('tok-123');
    setToken(null);
    expect(getToken()).toBeNull();
  });

  it('round-trips the tenant id as a string', () => {
    setBusinessId(7);
    expect(getBusinessId()).toBe('7');
    setBusinessId(null);
    expect(getBusinessId()).toBeNull();
  });

  it('clears both keys on logout', () => {
    setToken('stale');
    setBusinessId(9);
    clearSession();
    expect(getToken()).toBeNull();
    expect(getBusinessId()).toBeNull();
  });
});
