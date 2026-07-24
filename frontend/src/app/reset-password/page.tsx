"use client";

import Link from "next/link";
import { FormEvent, Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Navbar } from "@/components/navbar";
import { useTranslation } from "@/components/locale-provider";
import { getApiBase } from "@/lib/api-base";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function ResetPasswordForm() {
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = new FormData(e.currentTarget);
    try {
      const res = await fetch(`${getApiBase()}/api/v1/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: form.get("token"),
          new_password: form.get("new_password"),
        }),
      });
      const body = await res.json();
      if (!res.ok || !body.success) throw new Error(body.error?.message || "Failed");
      setMessage(t("auth.resetSuccess"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.requestFailed"));
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>{t("auth.resetPasswordTitle")}</CardTitle>
        <CardDescription>{t("auth.resetPasswordDesc")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="token">{t("auth.resetToken")}</Label>
            <Input
              id="token"
              name="token"
              required
              defaultValue={searchParams.get("token") ?? ""}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new_password">{t("settings.newPassword")}</Label>
            <Input id="new_password" name="new_password" type="password" required minLength={8} />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          {message && <p className="text-sm text-green-400">{message}</p>}
          <Button type="submit" className="w-full">
            {t("auth.resetPasswordBtn")}
          </Button>
        </form>
        <Link
          href="/login"
          className="mt-4 block text-center text-sm text-muted-foreground hover:underline"
        >
          {t("auth.backToLogin")}
        </Link>
      </CardContent>
    </Card>
  );
}

export default function ResetPasswordPage() {
  const { t } = useTranslation();

  return (
    <>
      <Navbar />
      <main className="container mx-auto flex max-w-md justify-center px-4 py-12">
        <Suspense fallback={<p className="text-muted-foreground">{t("common.loading")}</p>}>
          <ResetPasswordForm />
        </Suspense>
      </main>
    </>
  );
}
