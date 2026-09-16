import axios, { type AxiosInstance, type AxiosError } from 'axios';

import { clearSession, getBusinessId, getToken } from './session';

/**
 * HTTP client configuration.
 *
 * `API_ORIGIN` is the deployment-specific base URL injected at build time from
 * `NEXT_PUBLIC_API_URL`; there is deliberately no fallback to a hard-coded host
 * in production builds beyond the local default.
 */
export const API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(
  /\/$/,
  ''
);

/** Versioned client: every `/api/v1` domain call goes through this instance. */
export const api = axios.create({ baseURL: `${API_ORIGIN}/api/v1` });

/** Unversioned client for platform paths such as `/health`. */
export const rootApi = axios.create({ baseURL: API_ORIGIN });

/** Attach bearer-token + tenant headers and the global 401 redirect. */
export function attachSessionInterceptors(instance: AxiosInstance): void {
  if (typeof window === 'undefined') return;

  instance.interceptors.request.use((cfg) => {
    const token = getToken();
    const businessId = getBusinessId();
    if (token) cfg.headers.set('Authorization', `Bearer ${token}`);
    if (businessId) cfg.headers.set('X-Business-Id', businessId);
    return cfg;
  });

  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      if (error.response?.status === 401 && window.location.pathname !== '/login') {
        clearSession();
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  );
}

attachSessionInterceptors(api);
attachSessionInterceptors(rootApi);

interface DetailShape {
  detail?: unknown;
}

interface ValidationIssue {
  msg?: string;
}

/** Human-readable message for any failure the API can return. */
export function errMsg(error: unknown, fallback = 'Request failed'): string {
  const data = (error as { response?: { data?: unknown } } | null)?.response?.data;
  if (!data) return (error as Error | null)?.message || fallback;
  if (typeof data === 'string') return data;
  const detail = (data as DetailShape).detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((issue: ValidationIssue) => issue?.msg ?? JSON.stringify(issue)).join('; ');
  }
  // Our own error envelope: { error: { code, message } }
  const envelope = (data as { error?: { message?: string } }).error;
  if (envelope?.message) return envelope.message;
  return JSON.stringify(data);
}

/** Trigger a browser download for a binary report or invoice. */
export async function downloadBlob(path: string, filename: string): Promise<void> {
  const res = await api.get(path, { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([res.data]));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
