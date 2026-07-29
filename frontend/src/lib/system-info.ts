"use client";

import { useEffect, useState } from "react";

type SystemInfo = {
  public_registration_enabled: boolean;
};

let cached: SystemInfo | null = null;
let inflight: Promise<SystemInfo> | null = null;

export function fetchPublicSystemInfo(): Promise<SystemInfo> {
  if (cached) return Promise.resolve(cached);
  if (inflight) return inflight;
  inflight = fetch("/api/v1/system/info")
    .then((r) => r.json())
    .then((body) => {
      cached = body.data as SystemInfo;
      return cached;
    })
    .finally(() => {
      inflight = null;
    });
  return inflight;
}

export function usePublicRegistrationEnabled(): boolean | null {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  useEffect(() => {
    fetchPublicSystemInfo()
      .then((info) => setEnabled(info.public_registration_enabled))
      .catch(() => setEnabled(false));
  }, []);
  return enabled;
}
