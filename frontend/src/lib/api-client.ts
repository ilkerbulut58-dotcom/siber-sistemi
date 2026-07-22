"use client";

import { getApiBase } from "@/lib/api-base";
import { ensureFreshAccessToken, readStoredTokens, refreshAccessToken } from "@/lib/auth-tokens";

export type {
  Finding,
  FindingHistoryEntry,
  FindingUpdate,
  ScanJob,
  Organization,
  Project,
  Domain,
  VerificationInstructions,
  ScanProfile,
  QuickScanResult,
  Asset,
  AsmDiscoveryJob,
  AttackSurfaceSummary,
  MobileApplication,
  MobileUploadResult,
  SupportGrant,
  SiteProfile,
  SensitiveDataSummary,
  RiskBreakdown,
  RiskBreakdownItem,
  BenchmarkRun,
  QualitySummary,
} from "@/lib/api-types";

export interface APIResponse<T> {
  success: boolean;
  data: T | null;
  error: { code: string; message: string } | null;
}

async function resolveToken(explicit?: string | null): Promise<string | null> {
  if (explicit) return explicit;
  const fresh = await ensureFreshAccessToken();
  if (fresh) return fresh;
  return readStoredTokens()?.access_token ?? null;
}

async function performFetch(
  path: string,
  token: string | null,
  options: RequestInit
): Promise<{ res: Response; body: APIResponse<unknown> }> {
  const res = await fetch(`${getApiBase()}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers as Record<string, string> | undefined),
    },
  });
  const body = (await res.json()) as APIResponse<unknown>;
  return { res, body };
}

function isAuthError(status: number, body: APIResponse<unknown>): boolean {
  return status === 401 && body.error?.code === "INVALID_TOKEN";
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string | null } = {}
): Promise<T> {
  const { token: explicitToken, ...rest } = options;
  let token = await resolveToken(explicitToken);

  let { res, body } = await performFetch(path, token, rest);

  if (isAuthError(res.status, body)) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      token = refreshed;
      ({ res, body } = await performFetch(path, token, rest));
    }
  }

  if (!res.ok || !body.success || body.data === null) {
    throw new Error(body.error?.message || "Request failed");
  }
  return body.data as T;
}
