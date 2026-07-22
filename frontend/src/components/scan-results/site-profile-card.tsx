"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
  if (!profile) {
    return (
      <Card className="border-border/60 bg-card/80">
        <CardHeader>
          <CardTitle>Site Profili</CardTitle>
          <CardDescription>Tarama tamamlandığında DNS, TLS ve teknoloji özeti burada görünür.</CardDescription>
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
  const dns = (data.dns ?? {}) as Record<string, string[]>;
  const sensitive = profile.sensitive_data;

  return (
    <div className="space-y-4">
      <Card className="border-border/60 bg-card/80">
        <CardHeader>
          <CardTitle>Site Profili</CardTitle>
          <CardDescription>
            {profile.hostname} — pasif istihbarat (web taraması)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-1">
          <Row label="Sayfa başlığı" value={(data.page_title as string) ?? "—"} />
          <Row label="HTTP durum" value={String(http.status_code ?? "—")} />
          <Row
            label="TLS geçerlilik"
            value={
              tls.valid === true
                ? `Geçerli${tls.days_until_expiry != null ? ` (${tls.days_until_expiry} gün)` : ""}`
                : tls.valid === false
                  ? "Geçersiz / hata"
                  : "—"
            }
          />
          <Row
            label="Teknolojiler"
            value={
              technologies.length
                ? technologies.map((t) => t.name).filter(Boolean).join(", ")
                : "—"
            }
          />
          <Row
            label="CDN / WAF"
            value={cdnWaf.length ? cdnWaf.map((c) => c.name).join(", ") : "—"}
          />
          <Row label="SPF" value={email.spf_present ? "Var" : "Yok"} />
          <Row label="DMARC" value={email.dmarc_present ? "Var" : "Yok"} />
          {Object.entries(dns).slice(0, 4).map(([rtype, values]) => (
            <Row key={rtype} label={`DNS ${rtype}`} value={values.slice(0, 3).join(", ")} />
          ))}
        </CardContent>
      </Card>

      <Card className="border-amber-500/20 bg-amber-500/5">
        <CardHeader>
          <CardTitle className="text-base">Hassas Veri Analizi</CardTitle>
          <CardDescription>
            Şifre, banka ve ödeme bilgisi taraması web yanıtlarında yapılır — ASM değildir.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-md border border-border/50 bg-background/50 p-3 text-center">
            <p className="text-2xl font-bold">{sensitive.password_findings}</p>
            <p className="text-xs text-muted-foreground">Şifre / credential</p>
          </div>
          <div className="rounded-md border border-border/50 bg-background/50 p-3 text-center">
            <p className="text-2xl font-bold">{sensitive.bank_findings}</p>
            <p className="text-xs text-muted-foreground">Banka / IBAN</p>
          </div>
          <div className="rounded-md border border-border/50 bg-background/50 p-3 text-center">
            <p className="text-2xl font-bold">{sensitive.payment_findings}</p>
            <p className="text-xs text-muted-foreground">Kart / ödeme</p>
          </div>
          <div className="rounded-md border border-border/50 bg-background/50 p-3 text-center">
            <p className="text-2xl font-bold">{sensitive.other_secrets}</p>
            <p className="text-xs text-muted-foreground">Diğer secret</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
