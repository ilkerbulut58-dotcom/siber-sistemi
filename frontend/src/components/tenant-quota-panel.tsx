"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import { apiFetch, type OnboardingStatus, type Organization } from "@/lib/api-client";

export function TenantQuotaPanel() {
  const { getAccessToken } = useAuth();
  const { t } = useTranslation();
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const token = getAccessToken();
        const orgs = await apiFetch<Organization[]>("/api/v1/organizations", { token });
        if (!orgs[0]) return;
        const data = await apiFetch<OnboardingStatus>(
          `/api/v1/organizations/${orgs[0].id}/onboarding-status`,
          { token }
        );
        setOnboarding(data);
      } catch {
        setOnboarding(null);
      }
    }
    void load();
  }, [getAccessToken]);

  if (!onboarding?.daily_scan_quota) return null;

  const used = onboarding.daily_scan_count ?? 0;
  const total = onboarding.daily_scan_quota ?? 0;
  const remaining = Math.max(0, total - used);
  const resetAt = onboarding.quota_resets_at
    ? new Date(onboarding.quota_resets_at).toLocaleString()
    : "—";

  return (
    <dl className="grid gap-2 text-sm">
      <div className="flex justify-between gap-4 border-b border-white/5 pb-2">
        <dt className="text-muted-foreground">{t("settings.tenantQuotaUsed")}</dt>
        <dd>{used}</dd>
      </div>
      <div className="flex justify-between gap-4 border-b border-white/5 pb-2">
        <dt className="text-muted-foreground">{t("settings.tenantQuotaRemaining")}</dt>
        <dd>{remaining}</dd>
      </div>
      <div className="flex justify-between gap-4 border-b border-white/5 pb-2">
        <dt className="text-muted-foreground">{t("settings.tenantQuotaTotal")}</dt>
        <dd>{total}</dd>
      </div>
      <div className="flex justify-between gap-4 border-b border-white/5 pb-2">
        <dt className="text-muted-foreground">{t("settings.tenantQuotaReset")}</dt>
        <dd className="text-right font-mono text-xs">{resetAt}</dd>
      </div>
      <div className="flex justify-between gap-4 border-b border-white/5 pb-2">
        <dt className="text-muted-foreground">{t("settings.tenantConcurrency")}</dt>
        <dd>{onboarding.scan_concurrency_limit ?? 1}</dd>
      </div>
      <p className="text-xs text-muted-foreground">{t("settings.tenantQuotaIncludesFailed")}</p>
      <p className="text-xs text-muted-foreground">{t("settings.tenantQuotaActiveScan")}</p>
    </dl>
  );
}
