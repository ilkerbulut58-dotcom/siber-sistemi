"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "@/components/locale-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchHealth, fetchReadiness } from "@/lib/api";

export function HomeContent() {
  const { t } = useTranslation();
  const [health, setHealth] = useState<Awaited<ReturnType<typeof fetchHealth>> | null>(null);
  const [readiness, setReadiness] = useState<Awaited<ReturnType<typeof fetchReadiness>> | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchHealth(), fetchReadiness()])
      .then(([h, r]) => {
        setHealth(h);
        setReadiness(r);
      })
      .catch(() => setError(t("home.apiConnectionFailed")));
  }, [t]);

  return (
    <main className="min-h-screen">
      <div className="container mx-auto px-4 py-12">
        <div className="mb-12 text-center">
          <h1 className="mb-4 text-4xl font-bold tracking-tight">{t("home.title")}</h1>
          <p className="mx-auto mb-8 max-w-2xl text-lg text-muted-foreground">{t("home.subtitle")}</p>
          <div className="flex justify-center gap-3">
            <Link href="/register">
              <Button size="lg">
                {t("home.getStarted")} <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline">
                {t("common.login")}
              </Button>
            </Link>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>{t("home.apiStatus")}</CardTitle>
              <CardDescription>{t("home.apiStatusDesc")}</CardDescription>
            </CardHeader>
            <CardContent>
              {error ? (
                <p className="text-destructive">{error}</p>
              ) : health?.data ? (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t("common.status")}</span>
                    <span className="font-medium text-green-400">{health.data.status}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t("common.environment")}</span>
                    <span>{health.data.environment}</span>
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("home.infra")}</CardTitle>
              <CardDescription>{t("home.infraDesc")}</CardDescription>
            </CardHeader>
            <CardContent>
              {readiness?.data ? (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t("home.general")}</span>
                    <span className="text-green-400">{readiness.data.status}</span>
                  </div>
                  {Object.entries(readiness.data.checks).map(([name, status]) => (
                    <div key={name} className="flex justify-between capitalize">
                      <span className="text-muted-foreground">{name}</span>
                      <span className={status === "ok" ? "text-green-400" : "text-destructive"}>
                        {status}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">{t("home.cannotCheck")}</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("home.features")}</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li className="text-green-400">✓ {t("home.feature1")}</li>
                <li className="text-green-400">✓ {t("home.feature2")}</li>
                <li className="text-green-400">✓ {t("home.feature3")}</li>
                <li className="text-green-400">✓ {t("home.feature4")}</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
