"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslation } from "@/components/locale-provider";
import type { SiteProfile } from "@/lib/api-client";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-wrap justify-between gap-2 border-b border-border/40 py-2 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-right">{value}</span>
    </div>
  );
}

export function SiteProfileCard({ profile }: { profile: SiteProfile | null }) {
  const { t } = useTranslation();

  if (!profile) {
    return (
      <Card className="border-border/60 bg-card/80">
        <CardHeader>
          <CardTitle>{t("scanResults.siteProfile")}</CardTitle>
          <CardDescription>{t("analytics.siteProfilePending")}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const data = profile.profile;
  const tls = (data.tls ?? {}) as Record<string, unknown>;
  const http = (data.http ?? {}) as Record<string, unknown>;
  const email = (data.email_security ?? {}) as Record<string, unknown>;
  const technologies = (data.technologies ?? []) as Array<{ name?: string; category?: string }>;
  const cdnWaf = (data.cdn_waf ?? []) as Array<{ name?: string; type?: string }>;
  const dns = (data.dns ?? {}) as Record<string, unknown>;
  const sensitive = profile.sensitive_data ?? {
    password_findings: 0,
    bank_findings: 0,
    payment_findings: 0,
    other_secrets: 0,
    note: "",
  };

  const tlsLabel =
    tls.valid === true
      ? `${t("siteProfile.tlsValid")}${tls.days_until_expiry != null ? ` (${tls.days_until_expiry} ${t("siteProfile.daysSuffix")})` : ""}`
      : tls.valid === false
        ? t("siteProfile.tlsInvalid")
        : "—";

  return (
    <div className="space-y-4">
      <Card className="border-border/60 bg-card/80">
        <CardHeader>
          <CardTitle>{t("siteProfile.title")}</CardTitle>
          <CardDescription>{t("siteProfile.desc", { hostname: profile.hostname })}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-1">
          <Row label={t("siteProfile.pageTitle")} value={(data.page_title as string) ?? "—"} />
          <Row label={t("siteProfile.httpStatus")} value={String(http.status_code ?? "—")} />
          <Row label={t("siteProfile.tlsValidity")} value={tlsLabel} />
          <Row
            label={t("siteProfile.technologies")}
            value={
              technologies.length
                ? technologies.map((tech) => tech.name).filter(Boolean).join(", ")
                : "—"
            }
          />
          <Row
            label={t("siteProfile.cdnWaf")}
            value={cdnWaf.length ? cdnWaf.map((c) => c.name).join(", ") : "—"}
          />
          <Row label={t("siteProfile.spf")} value={email.spf_present ? t("siteProfile.present") : t("siteProfile.absent")} />
          <Row label={t("siteProfile.dmarc")} value={email.dmarc_present ? t("siteProfile.present") : t("siteProfile.absent")} />
          {Object.entries(dns).slice(0, 4).map(([rtype, values]) => (
            <Row
              key={rtype}
              label={`DNS ${rtype}`}
              value={
                Array.isArray(values)
                  ? values.slice(0, 3).join(", ")
                  : values != null
                    ? String(values)
                    : "—"
              }
            />
          ))}
        </CardContent>
      </Card>

      <Card className="border-amber-500/20 bg-amber-500/5">
        <CardHeader>
          <CardTitle className="text-base">{t("siteProfile.sensitiveTitle")}</CardTitle>
          <CardDescription>{t("siteProfile.sensitiveDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-md border border-border/50 bg-background/50 p-3 text-center">
            <p className="text-2xl font-bold">{sensitive.password_findings}</p>
            <p className="text-xs text-muted-foreground">{t("siteProfile.passwordLabel")}</p>
          </div>
          <div className="rounded-md border border-border/50 bg-background/50 p-3 text-center">
            <p className="text-2xl font-bold">{sensitive.bank_findings}</p>
            <p className="text-xs text-muted-foreground">{t("siteProfile.bankLabel")}</p>
          </div>
          <div className="rounded-md border border-border/50 bg-background/50 p-3 text-center">
            <p className="text-2xl font-bold">{sensitive.payment_findings}</p>
            <p className="text-xs text-muted-foreground">{t("siteProfile.paymentLabel")}</p>
          </div>
          <div className="rounded-md border border-border/50 bg-background/50 p-3 text-center">
            <p className="text-2xl font-bold">{sensitive.other_secrets}</p>
            <p className="text-xs text-muted-foreground">{t("siteProfile.otherSecretsLabel")}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
