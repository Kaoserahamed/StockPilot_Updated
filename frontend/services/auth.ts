/**
 * Authentication service (FR-1).
 *
 * The only place that knows the auth endpoint shapes; `lib/auth.tsx` and the
 * auth pages consume these functions instead of calling axios directly.
 */

import { api } from '@/lib/api';
import type { AuthUser, TokenPair } from '@/types';

export interface RegisterPayload {
  owner_name: string;
  business_name: string;
  password: string;
  email?: string;
  phone?: string;
}

export async function register(payload: RegisterPayload): Promise<AuthUser> {
  const { data } = await api.post<AuthUser>('/auth/register', payload);
  return data;
}

export async function login(username: string, password: string): Promise<TokenPair> {
  const { data } = await api.post<TokenPair>('/auth/login', { username, password });
  return data;
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout');
}

export async function me(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>('/auth/me');
  return data;
}

export async function refresh(refreshToken: string): Promise<TokenPair> {
  const { data } = await api.post<TokenPair>('/auth/refresh', { refresh_token: refreshToken });
  return data;
}

/** Returns a reset token in development; production would deliver it by email. */
export async function forgotPassword(
  username: string
): Promise<{ message: string; dev_token?: string }> {
  const { data } = await api.post('/auth/forgot-password', { username });
  return data;
}

export async function resetPassword(
  token: string,
  newPassword: string
): Promise<{ message: string }> {
  const { data } = await api.post('/auth/reset-password', {
    token,
    new_password: newPassword,
  });
  return data;
}
