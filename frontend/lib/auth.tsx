'use client';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import type { AuthUser } from '@/types';
import * as authService from '@/services/auth';
import { clearSession, getToken, setToken } from './session';

interface RegisterInput {
  owner_name: string;
  business_name: string;
  password: string;
  email?: string;
  phone?: string;
}

interface Ctx {
  user: AuthUser | null;
  loading: boolean;
  login(username: string, password: string): Promise<void>;
  register(payload: RegisterInput): Promise<void>;
  logout(): Promise<void>;
  refresh(): Promise<void>;
}

const AuthCtx = createContext<Ctx | null>(null);

export function useAuth(): Ctx {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await authService.me());
    } catch {
      setUser(null);
      clearSession();
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(
    async (username: string, password: string) => {
      const tokens = await authService.login(username, password);
      setToken(tokens.access_token);
      await refresh();
      router.push('/dashboard');
    },
    [refresh, router]
  );

  const register = useCallback(
    async (payload: RegisterInput) => {
      await authService.register(payload);
      await login(payload.email || payload.phone || '', payload.password);
    },
    [login]
  );

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } catch {
      // A failed logout must still clear the local session.
    }
    clearSession();
    setUser(null);
    router.push('/login');
  }, [router]);

  return (
    <AuthCtx.Provider value={{ user, loading, login, register, logout, refresh }}>
      {children}
    </AuthCtx.Provider>
  );
}
