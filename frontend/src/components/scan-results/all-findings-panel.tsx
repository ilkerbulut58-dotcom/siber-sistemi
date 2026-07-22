"use client";



import type { Finding } from "@/lib/api-client";

import { Button } from "@/components/ui/button";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { FindingRowCard } from "@/components/scan-results/finding-row-card";



interface Props {

  findings: Finding[];

  onOpenDetail: (id: string) => void;

}



export function AllFindingsPanel({ findings, onOpenDetail }: Props) {

  return (

    <Card className="border-border/60 bg-card/80" id="section-all-findings">

      <CardHeader>

        <CardTitle>Tüm Bulgular</CardTitle>

        <CardDescription>

          {findings.length} bulgu — detay için satıra tıklayın veya Detay butonunu kullanın

        </CardDescription>

      </CardHeader>

      <CardContent className="space-y-3">

        {findings.length === 0 ? (

          <p className="text-muted-foreground">Bulgu bulunamadı.</p>

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

