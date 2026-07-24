"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/components/auth-provider";
import { useTranslation } from "@/components/locale-provider";
import { apiFetch, type UserProfile } from "@/lib/api-client";
import { getApiBase } from "@/lib/api-base";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function SettingsPage() {
  const { getAccessToken, user } = useAuth();
  const { t, formatApiError } = useTranslation();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<UserProfile>("/api/v1/users/me", { token: getAccessToken() });
      setProfile(data);
    } catch (err) {
      setError(formatApiError(err));
    }
  }, [formatApiError, getAccessToken]);

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
    try {
      await fetch(`${getApiBase()}/api/v1/auth/resend-verification`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAccessToken()}`,
        },
      });
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
              {profile?.is_email_verified || user?.is_email_verified
                ? t("settings.emailVerified")
                : t("settings.emailNotVerified")}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {!profile?.is_email_verified && !user?.is_email_verified && (
              <>
                <Button type="button" variant="outline" onClick={() => void resendVerification()}>
                  {t("settings.resendVerification")}
                </Button>
                <Link href="/verify-email">
                  <Button type="button" variant="secondary">
                    {t("auth.verifyBtn")}
                  </Button>
                </Link>
              </>
            )}
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
