"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Navbar } from "@/components/navbar";
import { useTranslation } from "@/components/locale-provider";
import { getApiBase } from "@/lib/api-base";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const email = new FormData(e.currentTarget).get("email");
    try {
      const res = await fetch(`${getApiBase()}/api/v1/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const body = await res.json();
      if (!res.ok || !body.success) throw new Error(body.error?.message || "Failed");
      setMessage(t("auth.resetSent"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.requestFailed"));
    }
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto flex max-w-md justify-center px-4 py-12">
        <Card className="w-full">
          <CardHeader>
            <CardTitle>{t("auth.forgotPasswordTitle")}</CardTitle>
            <CardDescription>{t("auth.forgotPasswordDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="email">{t("auth.email")}</Label>
                <Input id="email" name="email" type="email" required />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              {message && <p className="text-sm text-green-400">{message}</p>}
              <Button type="submit" className="w-full">{t("auth.sendResetLink")}</Button>
            </form>
            <Link href="/login" className="mt-4 block text-center text-sm text-muted-foreground hover:underline">
              {t("auth.backToLogin")}
            </Link>
          </CardContent>
        </Card>
      </main>
    </>
  );
}
