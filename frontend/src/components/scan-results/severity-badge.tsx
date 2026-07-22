import { severityLabel } from "@/lib/i18n-tr";
import { cn } from "@/lib/utils";

const STYLES: Record<string, string> = {
  critical: "bg-red-500/20 text-red-300 border-red-500/40",
  high: "bg-orange-500/20 text-orange-300 border-orange-500/40",
  medium: "bg-yellow-500/20 text-yellow-200 border-yellow-500/40",
  low: "bg-blue-500/20 text-blue-300 border-blue-500/40",
  info: "bg-slate-500/20 text-slate-300 border-slate-500/40",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold",
        STYLES[severity] ?? STYLES.info
      )}
    >
      {severityLabel(severity)}
    </span>
  );
}

export function MiniRiskRing({ score }: { score: number | null | undefined }) {
  if (score == null) return null;
  const color =
    score >= 70 ? "#ef4444" : score >= 45 ? "#f97316" : score >= 25 ? "#eab308" : "#3b82f6";
  const pct = Math.min(100, score) / 100;
  const r = 14;
  const c = 2 * Math.PI * r;
  return (
    <svg width="36" height="36" className="shrink-0" aria-hidden>
      <circle cx="18" cy="18" r={r} fill="none" stroke="hsl(var(--border))" strokeWidth="3" />
      <circle
        cx="18"
        cy="18"
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="3"
        strokeDasharray={`${c * pct} ${c}`}
        strokeLinecap="round"
        transform="rotate(-90 18 18)"
      />
      <text x="18" y="21" textAnchor="middle" className="fill-foreground text-[8px] font-bold">
        {Math.round(score)}
      </text>
    </svg>
  );
}
