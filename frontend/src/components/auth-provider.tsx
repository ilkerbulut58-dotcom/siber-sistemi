"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getApiBase } from "@/lib/api-base";
import {
  getAccessTokenExpiryMs,
  readStoredTokens,
  refreshAccessToken,
  TOKENS_UPDATED_EVENT,
  writeStoredTokens,
} from "@/lib/auth-tokens";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string | null;
  is_email_verified: boolean;
  is_platform_admin: boolean;
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => string | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const USER_KEY = "siber_user";

async function authFetch(path: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(`${getApiBase()}${path}`, init);
  } catch {
    throw new Error("Sunucuya bağlanılamadı. Lütfen tekrar deneyin.");
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const storedTokens = readStoredTokens();
      const storedUser = localStorage.getItem(USER_KEY);
      if (storedTokens && storedUser) {
        setTokens(storedTokens);
        setUser(JSON.parse(storedUser));
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const syncTokens = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (detail?.access_token) {
        setTokens(detail);
        return;
      }
      const stored = readStoredTokens();
      if (stored) setTokens(stored);
    };
    window.addEventListener(TOKENS_UPDATED_EVENT, syncTokens);
    return () => window.removeEventListener(TOKENS_UPDATED_EVENT, syncTokens);
  }, []);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;

    const schedule = () => {
      if (cancelled) return;
      const current = readStoredTokens();
      if (!current?.access_token) return;

      const expMs = getAccessTokenExpiryMs(current.access_token);
      if (!expMs) return;

      const delay = Math.max(5_000, expMs - Date.now() - 2 * 60 * 1000);
      timer = setTimeout(async () => {
        if (cancelled) return;
        await refreshAccessToken();
        const updated = readStoredTokens();
        if (updated) setTokens(updated);
        schedule();
      }, delay);
    };

    schedule();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [tokens?.access_token]);

  const persist = useCallback((nextTokens: AuthTokens, nextUser: AuthUser) => {
    setTokens(nextTokens);
    setUser(nextUser);
    writeStoredTokens(nextTokens);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await authFetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const body = await res.json();
      if (!res.ok || !body.success) {
        throw new Error(body.error?.message || "Giriş başarısız");
      }
      persist(body.data.tokens, body.data.user);
    },
    [persist]
  );

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const res = await authFetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: fullName }),
      });
      const body = await res.json();
      if (!res.ok || !body.success) {
        throw new Error(body.error?.message || "Kayıt başarısız");
      }
      persist(body.data.tokens, body.data.user);
    },
    [persist]
  );

  const logout = useCallback(async () => {
    if (tokens?.refresh_token) {
      try {
        await authFetch("/api/v1/auth/logout", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${tokens.access_token}`,
          },
          body: JSON.stringify({ refresh_token: tokens.refresh_token }),
        });
      } catch {
        /* ignore */
      }
    }
    setTokens(null);
    setUser(null);
    localStorage.removeItem("siber_tokens");
    localStorage.removeItem(USER_KEY);
  }, [tokens]);

  const getAccessToken = useCallback(
    () => readStoredTokens()?.access_token ?? tokens?.access_token ?? null,
    [tokens]
  );

  const value = useMemo(
    () => ({ user, isLoading, login, register, logout, getAccessToken }),
    [user, isLoading, login, register, logout, getAccessToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
