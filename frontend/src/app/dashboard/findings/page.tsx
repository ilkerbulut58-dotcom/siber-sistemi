"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import {
  apiFetch,
  type OnboardingStatus,
  type Organization,
  type ScanJob,
} from "@/lib/api-client";

export default function FindingsRedirectPage() {
  const router = useRouter();
  const { getAccessToken } = useAuth();
  const { t } = useTranslation();

  useEffect(() => {
    async function go() {
      try {
        const token = getAccessToken();
        const orgs = await apiFetch<Organization[]>("/api/v1/organizations", { token });
        const org = orgs[0];
        if (!org) {
          router.replace("/dashboard");
          return;
        }
        const onboarding = await apiFetch<OnboardingStatus>(
          `/api/v1/organizations/${org.id}/onboarding-status`,
          { token }
        ).catch(() => null);
        if (onboarding?.latest_completed_scan_id) {
          router.replace(
            `/dashboard/${org.id}/scans/${onboarding.latest_completed_scan_id}#section-all-findings`
          );
          return;
        }
        const scans = await apiFetch<ScanJob[]>(`/api/v1/organizations/${org.id}/scans`, { token });
        const completed = scans.find((s) => s.status === "completed");
        if (completed) {
          router.replace(`/dashboard/${org.id}/scans/${completed.id}#section-all-findings`);
          return;
        }
        router.replace("/dashboard/scan");
      } catch {
        router.replace("/dashboard/scan");
      }
    }
    void go();
  }, [getAccessToken, router]);

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 py-12 text-muted-foreground">{t("common.loading")}</main>
    </>
  );
}
