import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import type { Finding } from "@/lib/api-types";
import { FindingDetailDrawer } from "@/components/scans/finding-detail-drawer";
import { baseFinding, sampleRiskBreakdown } from "@/test/finding-fixtures";

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn(),
}));

const { apiFetch } = await import("@/lib/api-client");

const sampleFinding: Finding = baseFinding({
  id: "finding-1",
  organization_id: "org-1",
  project_id: "proj-1",
  scan_job_id: "scan-1",
  source_rule_id: "missing-header-csp",
  title: "CSP başlığı eksik",
  description: "Content-Security-Policy tanımlı değil.",
  severity: "medium",
  confidence: "medium",
  correlation_key: "missing-header-content-security-policy",
  risk_score: 55,
  cvss_score: 5.0,
  source_tools: ["passive_http", "zap"],
  verification_status: "verified",
  verification_notes: "Header hâlâ eksik.",
  evidence: { missing_header: "content-security-policy", status_code: 200 },
  remediation: "CSP ekleyin.",
  risk_explanation: "XSS riski artabilir.",
  remediation_steps: ["Plesk paneline girin.", "nginx direktiflerini ekleyin."],
  config_file_paths: ["Plesk → Apache & nginx Settings"],
  config_snippet: 'add_header Content-Security-Policy "default-src self";',
  ai_summary: "CSP eksikliği XSS savunmasını zayıflatır.",
  ai_remediation: "Test ortamında CSP ekleyin.",
  ai_confidence_label: "unverified",
  risk_breakdown: sampleRiskBreakdown,
  risk_model_version: "1.0.0",
  first_seen_at: "2026-01-01T00:00:00Z",
  last_seen_at: "2026-01-02T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
});

describe("FindingDetailDrawer", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockImplementation(async (path: string) => {
      if (path.includes("/history")) return [];
      return sampleFinding;
    });
  });

  it("renders finding details when open", async () => {
    render(
      <FindingDetailDrawer
        open
        onOpenChange={() => {}}
        finding={sampleFinding}
        orgId="org-1"
        getAccessToken={() => "token"}
        onFindingUpdated={() => {}}
        onToast={() => {}}
        onRetestNavigate={() => {}}
        scanCompleted
      />
    );

    expect(screen.getByText("CSP başlığı eksik")).toBeInTheDocument();
    expect(screen.getByText(/XSS riski/)).toBeInTheDocument();
    expect(screen.getByText(/Korelasyon:/)).toBeInTheDocument();
    expect(screen.getAllByText(/ZAP/i).length).toBeGreaterThan(0);
  });

  it("shows risk breakdown section", () => {
    render(
      <FindingDetailDrawer
        open
        onOpenChange={() => {}}
        finding={sampleFinding}
        orgId="org-1"
        getAccessToken={() => "token"}
        onFindingUpdated={() => {}}
        onToast={() => {}}
        onRetestNavigate={() => {}}
      />
    );
    expect(screen.getByText("Risk açıklaması")).toBeInTheDocument();
    expect(screen.getByText("Önem derecesi")).toBeInTheDocument();
  });

  it("supports copy action on remediation code", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(
      <FindingDetailDrawer
        open
        onOpenChange={() => {}}
        finding={sampleFinding}
        orgId="org-1"
        getAccessToken={() => "token"}
        onFindingUpdated={() => {}}
        onToast={() => {}}
        onRetestNavigate={() => {}}
      />
    );

    fireEvent.click(screen.getByRole("tab", { name: "Nginx" }));
    const copyBtn = screen.getByRole("button", { name: /kodu kopyala/i });
    fireEvent.click(copyBtn);

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(expect.stringContaining("Content-Security-Policy"));
    });
  });

  it("shows AI fallback when summary missing", () => {
    render(
      <FindingDetailDrawer
        open
        onOpenChange={() => {}}
        finding={{ ...sampleFinding, ai_summary: null, ai_remediation: null }}
        orgId="org-1"
        getAccessToken={() => "token"}
        onFindingUpdated={() => {}}
        onToast={() => {}}
        onRetestNavigate={() => {}}
        scanCompleted={false}
      />
    );

    expect(screen.getByText(/AI analizi henüz hazır değil/)).toBeInTheDocument();
  });

  it("calls onOpenChange when closed via escape", async () => {
    const onOpenChange = vi.fn();
    render(
      <FindingDetailDrawer
        open
        onOpenChange={onOpenChange}
        finding={sampleFinding}
        orgId="org-1"
        getAccessToken={() => "token"}
        onFindingUpdated={() => {}}
        onToast={() => {}}
        onRetestNavigate={() => {}}
      />
    );

    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => {
      expect(onOpenChange).toHaveBeenCalled();
    });
  });

  it("shows risk breakdown fallback when API data missing", () => {
    render(
      <FindingDetailDrawer
        open
        onOpenChange={() => {}}
        finding={baseFinding({ risk_breakdown: null, risk_score: 42 })}
        orgId="org-1"
        getAccessToken={() => "token"}
        onFindingUpdated={() => {}}
        onToast={() => {}}
        onRetestNavigate={() => {}}
      />
    );
    expect(screen.getByText(/Risk dağılımı henüz hesaplanmadı/)).toBeInTheDocument();
    expect(screen.getByText(/Toplam puan: 42/)).toBeInTheDocument();
  });

  it("does not render HTML from malicious finding title", () => {
    render(
      <FindingDetailDrawer
        open
        onOpenChange={() => {}}
        finding={baseFinding({
          title: '<img src=x onerror="alert(1)"> XSS',
          ai_summary: '<script>alert("xss")</script>',
        })}
        orgId="org-1"
        getAccessToken={() => "token"}
        onFindingUpdated={() => {}}
        onToast={() => {}}
        onRetestNavigate={() => {}}
      />
    );
    expect(screen.getByText('<img src=x onerror="alert(1)"> XSS')).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector("img[src='x']")).toBeNull();
  });

  it("updates status via API", async () => {
    const onToast = vi.fn();
    const onFindingUpdated = vi.fn();
    vi.mocked(apiFetch).mockImplementation(async (path: string, opts?: RequestInit) => {
      if (path.includes("/history")) return [];
      if (opts?.method === "PATCH") {
        return { ...sampleFinding, status: "resolved" };
      }
      return sampleFinding;
    });

    render(
      <FindingDetailDrawer
        open
        onOpenChange={() => {}}
        finding={sampleFinding}
        orgId="org-1"
        getAccessToken={() => "token"}
        onFindingUpdated={onFindingUpdated}
        onToast={onToast}
        onRetestNavigate={() => {}}
      />
    );

    const select = screen.getByLabelText("Bulgu durumu");
    fireEvent.change(select, { target: { value: "resolved" } });

    await waitFor(() => {
      expect(onToast).toHaveBeenCalledWith("Bulgu durumu güncellendi.", "success");
    });
  });
});
