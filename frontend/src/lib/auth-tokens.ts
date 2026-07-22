"use client";

import { getApiBase } from "@/lib/api-base";

const TOKEN_KEY = "siber_tokens";
export const TOKENS_UPDATED_EVENT = "siber:tokens-updated";

export interface StoredTokens {
  access_token: string;
  refresh_token: string;
}

let refreshInFlight: Promise<string | null> | null = null;

export function readStoredTokens(): StoredTokens | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    return raw ? (JSON.parse(raw) as StoredTokens) : null;
  } catch {
    return null;
  }
}

export function writeStoredTokens(tokens: StoredTokens): void {
  localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  window.dispatchEvent(new CustomEvent(TOKENS_UPDATED_EVENT, { detail: tokens }));
}

export function getAccessTokenExpiryMs(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

export async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    const stored = readStoredTokens();
    if (!stored?.refresh_token) return null;

    try {
      const res = await fetch(`${getApiBase()}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: stored.refresh_token }),
      });
      const body = await res.json();
      if (!res.ok || !body.success) return null;

      const next: StoredTokens = {
        access_token: body.data.access_token,
        refresh_token: body.data.refresh_token,
      };
      writeStoredTokens(next);
      return next.access_token;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

/** Refresh access token shortly before it expires. */
export async function ensureFreshAccessToken(): Promise<string | null> {
  const stored = readStoredTokens();
  if (!stored?.access_token) return null;

  const expMs = getAccessTokenExpiryMs(stored.access_token);
  const refreshBufferMs = 2 * 60 * 1000;
  if (expMs && Date.now() < expMs - refreshBufferMs) {
    return stored.access_token;
  }

  return refreshAccessToken();
}
