import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { apiRequest, getToken, setToken } from '../services/api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // `loading` covers the initial token check, so protected routes do not flash
  // the login screen before we know whether the stored token is still good.
  const [loading, setLoading] = useState(Boolean(getToken()));

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    apiRequest('/api/auth/me/')
      .then((data) => {
        if (!cancelled) setUser(data);
      })
      .catch(() => {
        setToken(null);
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const applyAuth = useCallback((payload) => {
    setToken(payload.token);
    setUser(payload.user);
    return payload.user;
  }, []);

  const login = useCallback(
    async (email, password) =>
      applyAuth(await apiRequest('/api/auth/login/', {
        method: 'POST',
        auth: false,
        body: { email, password },
      })),
    [applyAuth],
  );

  const register = useCallback(
    async (email, password, fullName) =>
      applyAuth(await apiRequest('/api/auth/register/', {
        method: 'POST',
        auth: false,
        body: { email, password, full_name: fullName },
      })),
    [applyAuth],
  );

  const logout = useCallback(async () => {
    try {
      await apiRequest('/api/auth/logout/', { method: 'POST' });
    } catch {
      // The token may already be gone server-side; clearing locally is enough.
    }
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const data = await apiRequest('/api/auth/me/');
    setUser(data);
    return data;
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshUser, setUser }),
    [user, loading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside an AuthProvider.');
  return context;
}
