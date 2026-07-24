"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, Loader2, Mail, XCircle } from "lucide-react";
import { FormEvent, Suspense, useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Navbar } from "@/components/navbar";
import { useTranslation } from "@/components/locale-provider";
import { getApiBase } from "@/lib/api-base";
import { ApiError } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type VerifyStatus = "pending" | "verifying" | "success" | "expired" | "invalid" | "already";

function VerifyEmailContent() {
  const { t, formatApiError } = useTranslation();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, refreshUser } = useAuth();
  const tokenFromUrl = searchParams.get("token")?.trim() ?? "";
  const justRegistered = searchParams.get("registered") === "1";

  const [status, setStatus] = useState<VerifyStatus>(
    justRegistered && !tokenFromUrl ? "pending" : tokenFromUrl ? "verifying" : "pending"
  );
  const [error, setError] = useState<string | null>(null);
  const [manualToken, setManualToken] = useState(tokenFromUrl);

  const runVerify = useCallback(
    async (token: string) => {
      if (!token) return;
      setStatus("verifying");
      setError(null);
      try {
        const res = await fetch(`${getApiBase()}/api/v1/auth/verify-email`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        const body = await res.json();
        if (!res.ok || !body.success) {
          const code = body.error?.code || "REQUEST_FAILED";
          if (code === "TOKEN_EXPIRED") {
            setStatus("expired");
            return;
          }
          if (code === "INVALID_TOKEN" && user?.is_email_verified) {
            setStatus("already");
            return;
          }
          if (code === "INVALID_TOKEN") {
            setError(t("auth.verifyInvalid"));
            setStatus("invalid");
            return;
          }
          throw new ApiError(code, body.error?.message || "Verification failed");
        }
        await refreshUser();
        setStatus("success");
      } catch (err) {
        setError(formatApiError(err));
        setStatus("invalid");
      }
    },
    [formatApiError, refreshUser, t, user?.is_email_verified]
  );

  useEffect(() => {
    if (user?.is_email_verified) {
      setStatus("already");
      return;
    }
    if (tokenFromUrl) {
      void runVerify(tokenFromUrl);
    }
  }, [tokenFromUrl, runVerify, user?.is_email_verified]);

  async function verifyManual(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const token = new FormData(e.currentTarget).get("token");
    if (typeof token === "string" && token.trim()) {
      await runVerify(token.trim());
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>{t("auth.verifyEmailTitle")}</CardTitle>
        <CardDescription>
          {status === "pending" && justRegistered
            ? t("auth.registerCheckEmailBody")
            : t("auth.verifyEmailDescLink")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status === "verifying" && (
          <div className="flex items-center gap-3 rounded-md border border-border bg-muted/30 p-4">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <p className="text-sm">{t("auth.verifyVerifying")}</p>
          </div>
        )}

        {status === "success" && (
          <div className="space-y-4 rounded-md border border-green-500/30 bg-green-500/10 p-4">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-5 w-5 text-green-400" />
              <div>
                <p className="font-medium text-green-100">{t("auth.verifySuccessTitle")}</p>
                <p className="mt-1 text-sm text-muted-foreground">{t("auth.verifySuccessBody")}</p>
              </div>
            </div>
            <Button type="button" className="w-full" onClick={() => router.push("/dashboard")}>
              {t("auth.verifySuccessCta")}
            </Button>
          </div>
        )}

        {status === "already" && (
          <div className="flex items-start gap-3 rounded-md border border-green-500/30 bg-green-500/10 p-4">
            <CheckCircle2 className="mt-0.5 h-5 w-5 text-green-400" />
            <div>
              <p className="font-medium text-green-100">{t("auth.verifyAlready")}</p>
              <p className="mt-1 text-sm text-muted-foreground">{t("settings.emailVerifiedDetail")}</p>
            </div>
          </div>
        )}

        {status === "expired" && (
          <div className="space-y-3 rounded-md border border-amber-500/30 bg-amber-500/10 p-4">
            <div className="flex items-start gap-3">
              <XCircle className="mt-0.5 h-5 w-5 text-amber-400" />
              <p className="text-sm">{t("auth.verifyExpired")}</p>
            </div>
            <Link href="/dashboard/settings">
              <Button type="button" variant="outline" className="w-full">
                {t("settings.resendVerification")}
              </Button>
            </Link>
          </div>
        )}

        {status === "invalid" && error && (
          <div className="flex items-start gap-3 rounded-md border border-destructive/30 bg-destructive/10 p-4">
            <XCircle className="mt-0.5 h-5 w-5 text-destructive" />
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {status === "pending" && justRegistered && (
          <div className="flex items-start gap-3 rounded-md border border-border bg-muted/30 p-4">
            <Mail className="mt-0.5 h-5 w-5 text-primary" />
            <div>
              <p className="font-medium">{t("auth.registerCheckEmailTitle")}</p>
              <p className="mt-1 text-sm text-muted-foreground">{t("auth.registerCheckEmailBody")}</p>
            </div>
          </div>
        )}

        {(status === "pending" || status === "invalid" || status === "expired") && (
          <details className="rounded-md border border-border p-3">
            <summary className="cursor-pointer text-sm text-muted-foreground">
              {t("auth.verifyManualHint")}
            </summary>
            <form onSubmit={verifyManual} className="mt-3 space-y-3">
              <div className="space-y-2">
                <Label htmlFor="token">{t("auth.verifyToken")}</Label>
                <Input
                  id="token"
                  name="token"
                  value={manualToken}
                  onChange={(e) => setManualToken(e.target.value)}
                />
              </div>
              <Button type="submit" variant="secondary" className="w-full">
                {t("auth.verifyBtn")}
              </Button>
            </form>
          </details>
        )}

        <Link href="/dashboard" className="block text-center text-sm text-muted-foreground hover:underline">
          {t("auth.verifySuccessCta")}
        </Link>
        <Link href="/login" className="block text-center text-sm text-muted-foreground hover:underline">
          {t("auth.backToLogin")}
        </Link>
      </CardContent>
    </Card>
  );
}

export default function VerifyEmailPage() {
  const { t } = useTranslation();

  return (
    <>
      <Navbar />
      <main className="container mx-auto flex max-w-md justify-center px-4 py-12">
        <Suspense fallback={<p className="text-muted-foreground">{t("common.loading")}</p>}>
          <VerifyEmailContent />
        </Suspense>
      </main>
    </>
  );
}
