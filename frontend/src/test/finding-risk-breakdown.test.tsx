import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { FindingDetailDrawer } from "@/components/scans/finding-detail-drawer";
import { baseFinding, sampleRiskBreakdown } from "@/test/finding-fixtures";
import { renderWithLocale } from "@/test/render-with-locale";

describe("finding risk breakdown display", () => {
  it("renders API-provided breakdown items", () => {
    renderWithLocale(
      <FindingDetailDrawer
        open
        onOpenChange={() => {}}
        finding={baseFinding({ risk_breakdown: sampleRiskBreakdown, risk_score: 55 })}
        orgId="org-1"
        getAccessToken={() => "token"}
        onFindingUpdated={() => {}}
        onToast={() => {}}
        onRetestNavigate={() => {}}
      />
    );
    expect(screen.getByText("Önem derecesi")).toBeInTheDocument();
    expect(screen.getByText("55/100 taban")).toBeInTheDocument();
  });

  it("shows safe fallback without backend breakdown", () => {
    renderWithLocale(
      <FindingDetailDrawer
        open
        onOpenChange={() => {}}
        finding={baseFinding({ risk_breakdown: null, risk_score: 72 })}
        orgId="org-1"
        getAccessToken={() => "token"}
        onFindingUpdated={() => {}}
        onToast={() => {}}
        onRetestNavigate={() => {}}
      />
    );
    expect(screen.getByText(/Risk dağılımı henüz hesaplanmadı/)).toBeInTheDocument();
  });
});
