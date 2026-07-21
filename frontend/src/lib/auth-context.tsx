import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { apiFetch, apiFetchJson, setAccessToken, setUnauthorizedHandler } from '@/lib/api';

export type UserRole = 'super_admin' | 'company_admin' | 'manager' | 'hr' | 'employee';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  company_id: string | null;
}

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  login: (email: string, password: string, rememberMe: boolean) => Promise<void>;
  logout: () => Promise<void>;
  /** Adopt an access token already obtained elsewhere (accept-invite, password reset) as the active session. */
  setSession: (accessToken: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');

  const clearSession = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(clearSession);
    return () => setUnauthorizedHandler(null);
  }, [clearSession]);

  // Access token lives in memory only, so a full page reload loses it — silently
  // try to restore a session from the httpOnly refresh cookie on first mount.
  useEffect(() => {
    (async () => {
      const res = await fetch('/api/v1/auth/refresh', { method: 'POST', credentials: 'include' });
      if (!res.ok) {
        setStatus('unauthenticated');
        return;
      }
      const data = await res.json();
      setAccessToken(data.access_token);
      try {
        const me = await apiFetchJson<User>('/api/v1/auth/me');
        setUser(me);
        setStatus('authenticated');
      } catch {
        clearSession();
      }
    })();
  }, [clearSession]);

  const setSession = useCallback(async (accessToken: string) => {
    setAccessToken(accessToken);
    const me = await apiFetchJson<User>('/api/v1/auth/me');
    setUser(me);
    setStatus('authenticated');
  }, []);

  const login = useCallback(
    async (email: string, password: string, rememberMe: boolean) => {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password, remember_me: rememberMe }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? 'Login failed');
      }
      const data = await res.json();
      await setSession(data.access_token);
    },
    [setSession]
  );

  const logout = useCallback(async () => {
    await apiFetch('/api/v1/auth/logout', { method: 'POST' });
    clearSession();
  }, [clearSession]);

  return <AuthContext.Provider value={{ user, status, login, logout, setSession }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
