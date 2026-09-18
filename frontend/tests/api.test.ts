/**
 * Tests for `lib/api.ts`: error-message extraction, the session interceptors
 * (bearer + tenant headers and the global 401 redirect) and the binary download
 * helper.
 *
 * The interceptors are exercised through a hand-built instance, so the handlers
 * can be captured and driven directly without performing a real request.
 */

import { AxiosHeaders } from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api, attachSessionInterceptors, downloadBlob, errMsg } from '../lib/api';
import { getBusinessId, getToken, setBusinessId, setToken } from '../lib/session';

describe('errMsg', () => {
  it('returns a plain string payload unchanged', () => {
    expect(errMsg({ response: { data: 'boom' } })).toBe('boom');
  });

  it('extracts FastAPI string details', () => {
    expect(errMsg({ response: { data: { detail: 'Not found' } } })).toBe('Not found');
  });

  it('joins FastAPI validation error arrays', () => {
    const err = {
      response: { data: { detail: [{ msg: 'field required' }, { msg: 'bad value' }] } },
    };
    expect(errMsg(err)).toBe('field required; bad value');
  });

  it('falls back gracefully without a response', () => {
    expect(errMsg(new Error('network down'), 'fallback')).toBe('network down');
    expect(errMsg(null, 'fallback')).toBe('fallback');
  });

  it('unwraps our own { error: { message } } envelope', () => {
    expect(errMsg({ response: { data: { error: { message: 'Tenant mismatch' } } } })).toBe(
      'Tenant mismatch'
    );
  });

  it('stringifies anything else instead of showing "[object Object]"', () => {
    expect(errMsg({ response: { data: { unexpected: true } } })).toBe('{"unexpected":true}');
    // A validation issue without a `msg` is stringified rather than dropped.
    expect(errMsg({ response: { data: { detail: ['plain'] } } })).toBe('"plain"');
  });

  it('uses the default message when there is nothing to report', () => {
    expect(errMsg(undefined)).toBe('Request failed');
  });
});

describe('downloadBlob', () => {
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;

  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  });

  it('fetches the path as a blob, clicks an anchor and revokes the URL', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: new Blob(['csv']) });
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    await downloadBlob('/reports/sales?format=csv', 'sales.csv');

    expect(get).toHaveBeenCalledWith('/reports/sales?format=csv', { responseType: 'blob' });
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });
});

describe('session interceptors', () => {
  const originalLocation = window.location;

  interface Captured {
    request?: (config: { headers: AxiosHeaders }) => { headers: AxiosHeaders };
    response?: (error: unknown) => Promise<unknown>;
  }

  /** Build a stand-in instance so the interceptors can be captured and driven. */
  function capture(): Captured {
    const captured: Captured = {};
    const fake = {
      interceptors: {
        request: {
          use: (handler: Captured['request']) => {
            captured.request = handler;
          },
        },
        response: {
          use: (_ok: unknown, handler: Captured['response']) => {
            captured.response = handler;
          },
        },
      },
    };
    attachSessionInterceptors(fake as unknown as Parameters<typeof attachSessionInterceptors>[0]);
    return captured;
  }

  /** Point `window.location` at a page without navigating jsdom. */
  function stubPathname(pathname: string): void {
    Object.defineProperty(window, 'location', {
      configurable: true,
      writable: true,
      value: { pathname, href: '' },
    });
  }

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      writable: true,
      value: originalLocation,
    });
  });

  it('attaches the bearer token and tenant header to every request', () => {
    const handlers = capture();
    setToken('token-123');
    setBusinessId(7);

    const config = { headers: new AxiosHeaders() };
    handlers.request?.(config);

    expect(config.headers.get('Authorization')).toBe('Bearer token-123');
    expect(config.headers.get('X-Business-Id')).toBe('7');
  });

  it('keeps the request headers empty without a session', () => {
    const handlers = capture();
    const config = { headers: new AxiosHeaders() };
    handlers.request?.(config);

    expect(config.headers.get('Authorization')).toBeFalsy();
    expect(config.headers.get('X-Business-Id')).toBeFalsy();
  });

  it('clears the session and redirects to /login on a 401 elsewhere', async () => {
    const handlers = capture();
    setToken('expired-token');
    setBusinessId(3);
    stubPathname('/dashboard');

    await expect(handlers.response?.({ response: { status: 401 } })).rejects.toBeDefined();

    expect(getToken()).toBeNull();
    expect(getBusinessId()).toBeNull();
    expect(window.location.href).toBe('/login');
  });

  it('leaves a 401 on the login page alone and passes other errors through', async () => {
    const handlers = capture();
    setToken('expired-token');
    stubPathname('/login');

    await expect(handlers.response?.({ response: { status: 401 } })).rejects.toBeDefined();
    await expect(handlers.response?.({ response: { status: 500 } })).rejects.toBeDefined();

    expect(getToken()).toBe('expired-token');
    expect(window.location.href).toBe('');
  });
});
