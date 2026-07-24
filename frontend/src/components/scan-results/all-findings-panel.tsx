"use client";



import type { Finding } from "@/lib/api-client";

import { Button } from "@/components/ui/button";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { FindingRowCard } from "@/components/scan-results/finding-row-card";
import { useTranslation } from "@/components/locale-provider";



interface Props {

  findings: Finding[];

  onOpenDetail: (id: string) => void;

}



export function AllFindingsPanel({ findings, onOpenDetail }: Props) {
  const { t } = useTranslation();

  return (

    <Card className="border-border/60 bg-card/80" id="section-all-findings">

      <CardHeader>

        <CardTitle>{t("analytics.allFindingsTitle")}</CardTitle>

        <CardDescription>

          {t("analytics.allFindingsDesc", { count: findings.length })}

        </CardDescription>

      </CardHeader>

      <CardContent className="space-y-3">

        {findings.length === 0 ? (

          <p className="text-muted-foreground">{t("analytics.findingsNotFound")}</p>

        ) : (

          findings.map((finding) => (

            <FindingRowCard

              key={finding.id}

              finding={finding}

              onDetail={() => onOpenDetail(finding.id)}

              onRowClick={() => onOpenDetail(finding.id)}

            />

          ))

        )}

      </CardContent>

    </Card>

  );

}

