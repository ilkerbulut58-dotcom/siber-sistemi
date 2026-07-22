"use client";



import type { Finding } from "@/lib/api-client";

import { Button } from "@/components/ui/button";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { FindingRowCard } from "@/components/scan-results/finding-row-card";



interface Props {

  findings: Finding[];

  onOpenDetail: (id: string) => void;

  onViewAll?: () => void;

}



export function FindingHighlightsList({

  findings,

  onOpenDetail,

  onViewAll,

}: Props) {

  return (

    <Card className="border-border/60 bg-card/80" id="section-findings">

      <CardHeader className="flex flex-row items-center justify-between pb-2">

        <CardTitle className="text-lg">En Önemli Bulgular</CardTitle>

        {findings.length > 0 && onViewAll && (

          <Button type="button" variant="outline" size="sm" onClick={onViewAll}>

            Tüm Bulguları Görüntüle

          </Button>

        )}

      </CardHeader>

      <CardContent className="space-y-3">

        {findings.length === 0 ? (

          <p className="text-sm text-muted-foreground">Kritik bulgu tespit edilmedi.</p>

        ) : (

          findings.map((f) => (

            <FindingRowCard

              key={f.id}

              finding={f}

              compact

              onDetail={() => onOpenDetail(f.id)}

              onRowClick={() => onOpenDetail(f.id)}

            />

          ))

        )}

      </CardContent>

    </Card>

  );

}

