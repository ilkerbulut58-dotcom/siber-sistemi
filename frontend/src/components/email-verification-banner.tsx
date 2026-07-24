"use client";

import Link from "next/link";
import { MailWarning } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import { getApiBase } from "@/lib/api-base";
import { Button } from "@/components/ui/button";

export function EmailVerificationBanner() {
  const { user, getAccessToken } = useAuth();
  const { t, formatApiError } = useTranslation();

  if (!user || user.is_email_verified) return null;

  async function resend() {
    try {
      const res = await fetch(`${getApiBase()}/api/v1/auth/resend-verification`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAccessToken()}`,
        },
      });
      const body = await res.json();
      if (!res.ok || !body.success) {
        throw new Error(body.error?.message || "Failed");
      }
      alert(t("settings.verificationSent"));
    } catch (err) {
      alert(formatApiError(err));
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex gap-3">
        <MailWarning className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
        <div>
          <p className="font-medium text-amber-100">{t("dashboard.emailVerifyBannerTitle")}</p>
          <p className="mt-1 text-sm text-muted-foreground">{t("dashboard.emailVerifyBannerBody")}</p>
        </div>
      </div>
      <div className="flex shrink-0 flex-wrap gap-2">
        <Button type="button" variant="outline" size="sm" onClick={() => void resend()}>
          {t("dashboard.emailVerifyBannerResend")}
        </Button>
        <Link href="/dashboard/settings">
          <Button type="button" variant="secondary" size="sm">
            {t("dashboard.emailVerifyBannerCta")}
          </Button>
        </Link>
      </div>
    </div>
  );
}
