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

export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function verify(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const token = new FormData(e.currentTarget).get("token");
    try {
      const res = await fetch(`${getApiBase()}/api/v1/auth/verify-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      const body = await res.json();
      if (!res.ok || !body.success) throw new Error(body.error?.message || "Failed");
      setMessage(t("auth.verifySuccess"));
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
            <CardTitle>{t("auth.verifyEmailTitle")}</CardTitle>
            <CardDescription>{t("auth.verifyEmailDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={verify} className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="token">{t("auth.verifyToken")}</Label>
                <Input id="token" name="token" required />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              {message && <p className="text-sm text-green-400">{message}</p>}
              <Button type="submit" className="w-full">{t("auth.verifyBtn")}</Button>
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
