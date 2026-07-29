"use client";

import Link from "next/link";
import { CheckCircle2, Mail } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import { apiFetch, type UserProfile } from "@/lib/api-client";
import { getApiBase } from "@/lib/api-base";
import { ApiError } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SystemInfoPanel } from "@/components/system-info-panel";
import { TenantQuotaPanel } from "@/components/tenant-quota-panel";

export default function SettingsPage() {
  const { getAccessToken, user, refreshUser } = useAuth();
  const { t, formatApiError } = useTranslation();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const emailVerified = profile?.is_email_verified ?? user?.is_email_verified ?? false;

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<UserProfile>("/api/v1/users/me", { token: getAccessToken() });
      setProfile(data);
      await refreshUser();
    } catch (err) {
      setError(formatApiError(err));
    }
  }, [formatApiError, getAccessToken, refreshUser]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveProfile(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = new FormData(e.currentTarget);
    try {
      const updated = await apiFetch<UserProfile>("/api/v1/users/me", {
        method: "PATCH",
        token: getAccessToken(),
        body: JSON.stringify({ full_name: form.get("full_name") || null }),
      });
      setProfile(updated);
      setMessage(t("settings.profileSaved"));
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  async function changePassword(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = new FormData(e.currentTarget);
    try {
      await apiFetch("/api/v1/users/me/password", {
        method: "PATCH",
        token: getAccessToken(),
        body: JSON.stringify({
          current_password: form.get("current_password"),
          new_password: form.get("new_password"),
        }),
      });
      e.currentTarget.reset();
      setMessage(t("settings.passwordChanged"));
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  async function resendVerification() {
    setError(null);
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
        throw new ApiError(body.error?.code || "REQUEST_FAILED", body.error?.message || "Failed");
      }
      setMessage(t("settings.verificationSent"));
    } catch (err) {
      setError(formatApiError(err));
    }
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto max-w-2xl space-y-6 px-4 py-8">
        <div>
          <Link href="/dashboard" className="text-sm text-muted-foreground hover:underline">
            ← {t("common.back")}
          </Link>
          <h1 className="mt-2 text-3xl font-bold">{t("settings.title")}</h1>
          <p className="text-muted-foreground">{t("settings.desc")}</p>
        </div>
        {error && <p className="text-destructive">{error}</p>}
        {message && <p className="text-green-400">{message}</p>}

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.profile")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={saveProfile} className="space-y-3">
              <div className="space-y-2">
                <Label>{t("auth.email")}</Label>
                <Input value={profile?.email ?? user?.email ?? ""} disabled />
              </div>
              <div className="space-y-2">
                <Label htmlFor="full_name">{t("settings.fullName")}</Label>
                <Input
                  id="full_name"
                  name="full_name"
                  defaultValue={profile?.full_name ?? ""}
                />
              </div>
              <Button type="submit">{t("settings.saveProfile")}</Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.emailVerification")}</CardTitle>
            <CardDescription>
              {emailVerified ? t("settings.emailVerifiedDetail") : t("settings.emailNotVerified")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {emailVerified ? (
              <div className="flex items-center gap-2 text-green-400">
                <CheckCircle2 className="h-5 w-5" />
                <span>{t("settings.emailVerified")}</span>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="outline" onClick={() => void resendVerification()}>
                  {t("settings.resendVerification")}
                </Button>
                <Link href="/verify-email">
                  <Button type="button" variant="secondary">
                    {t("auth.verifyBtn")}
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              {t("settings.mailNotificationsTitle")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• {t("settings.mailFlowRegister")}</li>
              <li>• {t("settings.mailFlowVerify")}</li>
              <li>• {t("settings.mailFlowForgot")}</li>
              <li>• {t("settings.mailFlowReset")}</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.supportTitle")}</CardTitle>
            <CardDescription>{t("settings.supportDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>{t("settings.supportCritical")}</p>
            <p>{t("settings.supportStuckScan")}</p>
            <p>{t("settings.supportEmergency")}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.tenantQuotaTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <TenantQuotaPanel />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.systemInfoTitle")}</CardTitle>
            <CardDescription>{t("settings.systemInfoDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <SystemInfoPanel />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.password")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={changePassword} className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="current_password">{t("settings.currentPassword")}</Label>
                <Input id="current_password" name="current_password" type="password" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new_password">{t("settings.newPassword")}</Label>
                <Input id="new_password" name="new_password" type="password" required minLength={8} />
              </div>
              <Button type="submit">{t("settings.changePassword")}</Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </>
  );
}
