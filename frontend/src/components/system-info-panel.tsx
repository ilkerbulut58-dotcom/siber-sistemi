"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "@/components/locale-provider";
import { apiFetch } from "@/lib/api-client";

type SystemInfo = {
  product: string;
  environment: string;
  version: string;
  git_commit: string;
  release_tag: string;
  domain_verification_required: boolean;
  scan_daily_quota: number;
  scan_concurrency_limit: number;
  allowed_profiles: string[];
  full_active_enabled: boolean;
  scan_notifications: string;
  public_registration_enabled: boolean;
};

export function SystemInfoPanel() {
  const { t } = useTranslation();
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<SystemInfo>("/api/v1/system/info")
      .then(setInfo)
      .catch(() => setError(t("settings.systemInfoError")));
  }, [t]);

  if (error) return <p className="text-sm text-destructive">{error}</p>;
  if (!info) return <p className="text-sm text-muted-foreground">{t("common.loading")}</p>;

  const rows: [string, string][] = [
    [t("settings.systemProduct"), info.product],
    [t("settings.systemEnvironment"), info.environment],
    [t("settings.systemVersion"), info.version],
    [t("settings.systemCommit"), info.git_commit || "—"],
    [t("settings.systemRelease"), info.release_tag],
    [t("settings.systemDomainVerification"), info.domain_verification_required ? t("common.yes") : t("common.no")],
    [t("settings.systemQuota"), String(info.scan_daily_quota)],
    [t("settings.systemConcurrency"), String(info.scan_concurrency_limit)],
    [t("settings.systemProfiles"), info.allowed_profiles.join(", ")],
    [t("settings.systemNotifications"), info.scan_notifications],
    [t("settings.systemRegistration"), info.public_registration_enabled ? t("common.yes") : t("common.no")],
  ];

  return (
    <dl className="grid gap-2 text-sm">
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between gap-4 border-b border-white/5 pb-2">
          <dt className="text-muted-foreground">{label}</dt>
          <dd className="text-right font-mono text-xs">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
