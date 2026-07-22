import { describe, it, expect } from "vitest";
import {
  computeSecurityScore,
  countBySeverity,
  getHeaderStatuses,
  scoreToLevel,
} from "@/lib/scan-analytics";
import { baseFinding } from "@/test/finding-fixtures";

describe("scan-analytics", () => {
  it("computes high score when no findings", () => {
    const r = computeSecurityScore([]);
    expect(r.score).toBeGreaterThanOrEqual(90);
    expect(r.level).toBe("strong");
  });

  it("lowers score with high risk findings", () => {
    const r = computeSecurityScore([
      baseFinding({ severity: "critical", risk_score: 85 }),
      baseFinding({ id: "2", severity: "high", risk_score: 70 }),
    ]);
    expect(r.score).toBeLessThan(60);
  });

  it("detects missing headers", () => {
    const statuses = getHeaderStatuses([
      baseFinding({ correlation_key: "missing-header-x-frame-options" }),
    ]);
    const xfo = statuses.find((h) => h.key === "x-frame-options");
    expect(xfo?.status).toBe("missing");
  });

  it("maps score to level", () => {
    expect(scoreToLevel(35)).toBe("critical");
    expect(scoreToLevel(68)).toBe("medium");
    expect(scoreToLevel(92)).toBe("strong");
  });

  it("counts severities", () => {
    const c = countBySeverity([
      baseFinding({ severity: "high" }),
      baseFinding({ id: "2", severity: "high" }),
      baseFinding({ id: "3", severity: "low" }),
    ]);
    expect(c.high).toBe(2);
    expect(c.low).toBe(1);
  });
});
