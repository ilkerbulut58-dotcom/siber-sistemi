"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import type { VerificationInstructions } from "@/lib/api-client";
import { useTranslation } from "@/components/locale-provider";
import { Button } from "@/components/ui/button";

function CopyField({
  label,
  value,
  copyLabel,
  copiedLabel,
}: {
  label: string;
  value: string;
  copyLabel: string;
  copiedLabel: string;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div className="flex items-start gap-2 rounded-md border border-border/60 bg-muted/20 p-2">
        <code className="min-w-0 flex-1 break-all text-xs">{value}</code>
        <Button type="button" size="sm" variant="ghost" className="h-8 shrink-0" onClick={() => void copy()}>
          {copied ? (
            <>
              <Check className="mr-1 h-3 w-3" />
              {copiedLabel}
            </>
          ) : (
            <>
              <Copy className="mr-1 h-3 w-3" />
              {copyLabel}
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

export function DomainVerificationPanel({ instructions }: { instructions: VerificationInstructions }) {
  const { t } = useTranslation();

  return (
    <div className="mt-4 space-y-4 rounded-md border border-border/60 bg-muted/20 p-4 text-sm">
      <p className="font-medium">
        {instructions.hostname} — {instructions.method}
      </p>
      <p className="text-muted-foreground">{t("project.verificationWhy")}</p>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-md border border-border/40 p-2">
          <p className="text-xs font-semibold">{t("project.methodDns")}</p>
        </div>
        <div className="rounded-md border border-border/40 p-2">
          <p className="text-xs font-semibold">{t("project.methodFile")}</p>
        </div>
        <div className="rounded-md border border-border/40 p-2">
          <p className="text-xs font-semibold">{t("project.methodMeta")}</p>
        </div>
      </div>

      {instructions.dns_host && instructions.dns_value && (
        <div className="space-y-3">
          <CopyField
            label={t("project.dnsHost")}
            value={instructions.dns_host}
            copyLabel={t("findingDrawer.copyCode")}
            copiedLabel={t("findingDrawer.copied")}
          />
          <CopyField
            label={t("project.dnsValue")}
            value={instructions.dns_value}
            copyLabel={t("findingDrawer.copyCode")}
            copiedLabel={t("findingDrawer.copied")}
          />
          {instructions.ttl_recommendation_seconds != null && (
            <p className="text-xs text-muted-foreground">
              {t("project.ttlRecommendation", { seconds: instructions.ttl_recommendation_seconds })}
            </p>
          )}
        </div>
      )}

      {instructions.well_known_url && instructions.well_known_content && (
        <div className="space-y-3">
          <CopyField
            label={t("project.wellKnownUrl")}
            value={instructions.well_known_url}
            copyLabel={t("findingDrawer.copyCode")}
            copiedLabel={t("findingDrawer.copied")}
          />
          <CopyField
            label={t("project.wellKnownContent")}
            value={instructions.well_known_content}
            copyLabel={t("findingDrawer.copyCode")}
            copiedLabel={t("findingDrawer.copied")}
          />
        </div>
      )}

      {instructions.meta_tag_html && (
        <CopyField
          label={t("project.metaTagHtml")}
          value={instructions.meta_tag_html}
          copyLabel={t("findingDrawer.copyCode")}
          copiedLabel={t("findingDrawer.copied")}
        />
      )}

      <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">
        {instructions.instructions.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>

      <ul className="space-y-1 text-xs text-muted-foreground">
        <li>{t("project.propagationNote")}</li>
        <li>{t("project.validityNote", { days: instructions.verification_valid_days ?? 30 })}</li>
        <li>{t("project.revokeNote")}</li>
        <li>{t("project.manualApprovalNote")}</li>
      </ul>
    </div>
  );
}
