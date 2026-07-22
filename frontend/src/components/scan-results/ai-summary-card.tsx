"use client";

import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  summary: string;
  priorities: string[];
  firstSteps: string[];
  onExpand?: () => void;
}

export function AISummaryCard({ summary, priorities, firstSteps, onExpand }: Props) {
  return (
    <Card className="border-violet-500/30 bg-gradient-to-br from-violet-500/10 via-card/90 to-indigo-500/5 shadow-[0_0_32px_-8px_rgba(139,92,246,0.35)]">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-5 w-5 text-violet-400" />
          AI Genel Değerlendirme
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <p className="leading-relaxed text-foreground/90">{summary}</p>
        {priorities.length > 0 && (
          <div>
            <p className="mb-2 font-medium text-violet-200">Kritik öncelikler</p>
            <ul className="flex flex-wrap gap-2">
              {priorities.map((p) => (
                <li
                  key={p}
                  className="rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs"
                >
                  {p}
                </li>
              ))}
            </ul>
          </div>
        )}
        {firstSteps.length > 0 && (
          <div>
            <p className="mb-2 font-medium text-violet-200">Önerilen düzeltme sırası</p>
            <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">
              {firstSteps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>
          </div>
        )}
        {onExpand && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="border-violet-500/40 text-violet-200 hover:bg-violet-500/10"
            onClick={onExpand}
          >
            AI Analizini Tam Gör
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
