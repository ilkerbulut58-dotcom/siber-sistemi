import { describe, it, expect } from "vitest";
import { buildRemediationTabs } from "@/lib/finding-remediation";
import type { Finding } from "@/lib/api-types";

describe("finding-remediation", () => {
  it("builds multi-platform tabs for security header findings", () => {
    const finding = {
      correlation_key: "missing-header-x-frame-options",
      remediation_steps: [
        "Hosting ortamınıza uygun yöntemi seçin.",
        "Yapılandırmayı kaydedin.",
      ],
      config_file_paths: [
        "[Nginx] /etc/nginx/sites-available/example.com",
        "[Nginx/Plesk] Plesk → example.com → Apache & nginx Settings",
        "[Apache] Site kökünde .htaccess",
        "[cPanel/WHM] Domains → example.com",
        "[Cloudflare] Dashboard → Transform Rules",
      ],
      config_snippet: 'add_header X-Frame-Options "SAMEORIGIN" always;',
      remediation: "X-Frame-Options ekleyin.",
    } as Finding;

    const tabs = buildRemediationTabs(finding);
    const ids = tabs.map((t) => t.id);
    expect(ids).toContain("general");
    expect(ids).toContain("nginx");
    expect(ids).toContain("apache");
    expect(ids).toContain("plesk");
    expect(ids).toContain("cpanel");
    expect(ids).toContain("cloudflare");
    expect(tabs.find((t) => t.id === "nginx")?.code).toContain("add_header");
    expect(tabs.find((t) => t.id === "apache")?.code).toContain("Header set");
  });

  it("does not require plesk-only steps in general tab", () => {
    const finding = {
      remediation_steps: ["Plesk paneline girin.", "Genel adım."],
      config_file_paths: ["[Nginx] /etc/nginx/sites-available/test.com"],
      config_snippet: "add_header X-Content-Type-Options nosniff always;",
      remediation: "Header ekleyin.",
      correlation_key: "missing-header-x-content-type-options",
    } as Finding;

    const tabs = buildRemediationTabs(finding);
    const general = tabs.find((t) => t.id === "general");
    expect(general?.steps.some((s) => s.toLowerCase().includes("plesk"))).toBe(false);
    expect(general?.steps.some((s) => s.includes("Genel"))).toBe(true);
  });
});
