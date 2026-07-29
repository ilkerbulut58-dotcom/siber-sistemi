"use client";

import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Globe,
  Radar,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";
import { useTranslation } from "@/components/locale-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { usePublicRegistrationEnabled } from "@/lib/system-info";

export function HomeContent() {
  const { t } = useTranslation();
  const registrationOpen = usePublicRegistrationEnabled();

  const steps = [
    { n: "1", title: t("home.step1Title"), desc: t("home.step1Desc"), icon: Globe },
    { n: "2", title: t("home.step2Title"), desc: t("home.step2Desc"), icon: Zap },
    { n: "3", title: t("home.step3Title"), desc: t("home.step3Desc"), icon: BarChart3 },
  ];

  const features = [
    {
      title: t("home.featureScanTitle"),
      desc: t("home.featureScanDesc"),
      icon: Shield,
    },
    {
      title: t("home.featureReportTitle"),
      desc: t("home.featureReportDesc"),
      icon: BarChart3,
    },
    {
      title: t("home.featureAiTitle"),
      desc: t("home.featureAiDesc"),
      icon: Sparkles,
    },
    {
      title: t("home.featureAsmTitle"),
      desc: t("home.featureAsmDesc"),
      icon: Radar,
    },
  ];

  return (
    <div className="hero-gradient min-h-screen">
      <section className="container mx-auto px-4 pb-16 pt-16 md:pb-24 md:pt-24">
        <div className="mx-auto max-w-4xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm text-primary">
            <Shield className="h-4 w-4" />
            {t("home.badge")}
          </div>
          <h1 className="mb-6 text-4xl font-bold tracking-tight md:text-5xl lg:text-6xl">
            {t("home.title")}
          </h1>
          <p className="mx-auto mb-10 max-w-2xl text-lg text-muted-foreground md:text-xl">
            {t("home.subtitle")}
          </p>
          <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
            {registrationOpen !== false && (
            <Link href="/register">
              <Button size="lg" className="glow-primary min-w-[200px]">
                {t("home.getStarted")} <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            )}
            <Link href="/login">
              <Button size="lg" variant="outline" className="min-w-[200px] border-white/15 bg-white/5">
                {t("home.signIn")}
              </Button>
            </Link>
          </div>
          <p className="mt-8 text-sm text-muted-foreground">{t("home.trustLine")}</p>
        </div>

        <div className="mx-auto mt-16 max-w-5xl">
          <Card className="glass-card overflow-hidden border-primary/20">
            <CardHeader className="border-b border-white/5 pb-4">
              <CardDescription className="text-xs uppercase tracking-wider text-primary">
                {t("home.previewLabel")}
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-6 p-6 md:grid-cols-[1fr_2fr]">
              <div className="flex flex-col items-center justify-center rounded-xl border border-white/10 bg-background/50 p-6">
                <div className="relative flex h-28 w-28 items-center justify-center rounded-full border-4 border-primary/30 bg-primary/5">
                  <span className="text-3xl font-bold text-gradient">B+</span>
                </div>
                <p className="mt-3 text-sm font-medium">{t("home.previewScore")}</p>
                <p className="text-2xl font-semibold">78</p>
              </div>
              <div className="space-y-3">
                <p className="text-sm font-medium text-muted-foreground">{t("home.previewFindings")}</p>
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-center">
                    <p className="text-2xl font-bold text-red-400">2</p>
                    <p className="text-xs text-muted-foreground">{t("home.previewCritical")}</p>
                  </div>
                  <div className="rounded-lg border border-orange-500/30 bg-orange-500/10 p-4 text-center">
                    <p className="text-2xl font-bold text-orange-400">5</p>
                    <p className="text-xs text-muted-foreground">{t("home.previewHigh")}</p>
                  </div>
                  <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4 text-center">
                    <p className="text-2xl font-bold text-yellow-400">12</p>
                    <p className="text-xs text-muted-foreground">{t("home.previewMedium")}</p>
                  </div>
                </div>
                <div className="space-y-2 pt-2">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 rounded-md border border-white/5 bg-muted/20 px-3 py-2"
                    >
                      <span className="h-2 w-2 rounded-full bg-orange-400" />
                      <span className="h-2 flex-1 rounded bg-muted/40" />
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="border-t border-white/5 bg-background/40 py-20">
        <div className="container mx-auto px-4">
          <h2 className="mb-12 text-center text-2xl font-semibold md:text-3xl">
            {t("home.howItWorks")}
          </h2>
          <div className="mx-auto grid max-w-5xl gap-8 md:grid-cols-3">
            {steps.map(({ n, title, desc, icon: Icon }) => (
              <div key={n} className="relative text-center">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-primary/30 bg-primary/10">
                  <Icon className="h-6 w-6 text-primary" />
                </div>
                <span className="mb-2 inline-block text-xs font-medium text-primary">0{n}</span>
                <h3 className="mb-2 font-semibold">{title}</h3>
                <p className="text-sm text-muted-foreground">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="container mx-auto px-4 py-20">
        <h2 className="mb-12 text-center text-2xl font-semibold md:text-3xl">
          {t("home.featuresTitle")}
        </h2>
        <div className="mx-auto grid max-w-5xl gap-6 sm:grid-cols-2">
          {features.map(({ title, desc, icon: Icon }) => (
            <Card key={title} className="glass-card border-white/10 transition-colors hover:border-primary/30">
              <CardHeader>
                <CardTitle className="flex items-center gap-3 text-lg">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Icon className="h-5 w-5 text-primary" />
                  </span>
                  {title}
                </CardTitle>
                <CardDescription className="text-base leading-relaxed">{desc}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
        <div className="mt-16 text-center">
          {registrationOpen !== false && (
          <Link href="/register">
            <Button size="lg">
              {t("home.getStarted")} <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
          )}
        </div>
      </section>
    </div>
  );
}
