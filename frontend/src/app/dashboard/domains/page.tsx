"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import { apiFetch, type OnboardingStatus, type Organization, type Project } from "@/lib/api-client";

export default function DomainsRedirectPage() {
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
        const projectId = onboarding?.first_project_id;
        if (projectId) {
          router.replace(`/dashboard/${org.id}/projects/${projectId}`);
          return;
        }
        const projects = await apiFetch<Project[]>(`/api/v1/organizations/${org.id}/projects`, {
          token,
        });
        if (projects[0]) {
          router.replace(`/dashboard/${org.id}/projects/${projects[0].id}`);
          return;
        }
        router.replace(`/dashboard/${org.id}`);
      } catch {
        router.replace("/dashboard");
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
