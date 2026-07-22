"use client";

import { scoreColor, type SecurityScoreResult } from "@/lib/scan-analytics";

interface Props {
  result: SecurityScoreResult;
  delta?: number | null;
}

export function SecurityScoreGauge({ result, delta }: Props) {
  const { score, label } = result;
  const color = scoreColor(score);
  const angle = (score / 100) * 180;
  const rad = (angle * Math.PI) / 180;

  return (
    <div className="flex flex-col items-center">
      <div className="relative h-[140px] w-[220px]">
        <svg viewBox="0 0 220 130" className="h-full w-full">
          <defs>
            <linearGradient id="gaugeTrack" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#ef4444" />
              <stop offset="35%" stopColor="#f97316" />
              <stop offset="55%" stopColor="#eab308" />
              <stop offset="100%" stopColor="#22c55e" />
            </linearGradient>
          </defs>
          <path
            d="M 30 110 A 80 80 0 0 1 190 110"
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth="12"
            strokeLinecap="round"
          />
          <path
            d="M 30 110 A 80 80 0 0 1 190 110"
            fill="none"
            stroke="url(#gaugeTrack)"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${(angle / 180) * 251} 251`}
            opacity={0.35}
          />
          <line
            x1="110"
            y1="110"
            x2={110 + 65 * Math.cos(Math.PI - rad)}
            y2={110 - 65 * Math.sin(rad)}
            stroke={color}
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="110" cy="110" r="6" fill={color} />
        </svg>
        <div className="absolute inset-x-0 bottom-2 text-center">
          <div className="text-4xl font-bold tabular-nums" style={{ color }}>
            {score}
          </div>
          <div className="text-xs text-muted-foreground">/ 100</div>
        </div>
      </div>
      <p className="mt-1 text-lg font-semibold" style={{ color }}>
        {label}
      </p>
      {delta != null && (
        <p
          className={`mt-1 text-sm font-medium ${delta >= 0 ? "text-green-400" : "text-red-400"}`}
        >
          {delta >= 0 ? "+" : ""}
          {delta} önceki taramaya göre
        </p>
      )}
    </div>
  );
}
