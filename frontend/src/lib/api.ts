import { getApiBase } from "@/lib/api-base";

export interface APIResponse<T> {
  success: boolean;
  data: T | null;
  error: {
    code: string;
    message: string;
    details?: unknown[];
  } | null;
  meta: {
    request_id?: string;
  };
}

export interface HealthStatus {
  status: string;
  version: string;
  environment: string;
  skip_domain_verification?: boolean;
}

export interface ReadinessStatus extends HealthStatus {
  checks: Record<string, string>;
}

export async function fetchHealth(): Promise<APIResponse<HealthStatus>> {
  const res = await fetch(`${getApiBase()}/api/v1/health`, {
    next: { revalidate: 0 },
  });
  return res.json();
}

export async function fetchReadiness(): Promise<APIResponse<ReadinessStatus>> {
  const res = await fetch(`${getApiBase()}/api/v1/health/ready`, {
    next: { revalidate: 0 },
  });
  return res.json();
}
