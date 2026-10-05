// owner: Krrish (T3) — auth context and route guards
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { registerTokenGetter, onUnauthorized } from '@/api/client';
import { authApi } from '@/api/endpoints/auth';

export interface AuthUser {
  id: string;
  username: string;
  is_admin: boolean;
  created_at: string;
  entry_count: number;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  login: (token: string, user: AuthUser) => void;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Token in memory + sessionStorage (never localStorage, AGENTS.md §3)
  const [token, setToken] = useState<string | null>(() => {
    return sessionStorage.getItem('hv-token');
  });

  const [user, setUser] = useState<AuthUser | null>(() => {
    const stored = sessionStorage.getItem('hv-user');
    if (!stored) return null;
    try {
      return JSON.parse(stored) as AuthUser;
    } catch {
      return null;
    }
  });

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const tokenRef = useRef<string | null>(token);
  tokenRef.current = token;

  // Register token getter for apiFetch
  useEffect(() => {
    registerTokenGetter(() => tokenRef.current);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    sessionStorage.removeItem('hv-token');
    sessionStorage.removeItem('hv-user');
  }, []);

  // Listen for global 401 unauthorized events
  useEffect(() => {
    const unsubscribe = onUnauthorized(() => {
      logout();
    });
    return unsubscribe;
  }, [logout]);

  const login = useCallback((newToken: string, newUser: AuthUser) => {
    setToken(newToken);
    setUser(newUser);
    sessionStorage.setItem('hv-token', newToken);
    sessionStorage.setItem('hv-user', JSON.stringify(newUser));
  }, []);

  const refreshUser = useCallback(async () => {
    if (!tokenRef.current) return;
    try {
      setIsLoading(true);
      const me = await authApi.me();
      const updatedUser: AuthUser = {
        id: me.id,
        username: me.username,
        is_admin: me.is_admin,
        created_at: me.created_at,
        entry_count: me.entry_count,
      };
      setUser(updatedUser);
      sessionStorage.setItem('hv-user', JSON.stringify(updatedUser));
    } catch {
      // If fetching /me fails (e.g. invalid token), logout
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  // Sync user profile from server on initial mount if token exists
  useEffect(() => {
    if (token) {
      void refreshUser();
    }
  }, [token, refreshUser]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        logout,
        isAuthenticated: !!user && !!token,
        isLoading,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

/** Redirects to /login if not authenticated, remembering previous location */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-140px)] items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
          <p className="text-sm text-[var(--text-secondary)]">Authenticating...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

/** Redirects to / if not admin */
export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-140px)] items-center justify-center p-8">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated || !user?.is_admin) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
