import { describe, it, expect } from "vitest";
import { buildRemediationTabs } from "@/lib/finding-remediation";
import type { Finding } from "@/lib/api-types";

describe("finding-remediation", () => {
  it("builds plesk and nginx tabs from finding data", () => {
    const finding = {
      remediation_steps: ["Plesk paneline girin.", "nginx direktiflerini ekleyin."],
      config_file_paths: ["Plesk → Apache & nginx Settings"],
      config_snippet: 'add_header X-Frame-Options "SAMEORIGIN";',
      remediation: "Header ekleyin.",
    } as Finding;

    const tabs = buildRemediationTabs(finding);
    expect(tabs.some((t) => t.id === "plesk")).toBe(true);
    expect(tabs.some((t) => t.id === "nginx")).toBe(true);
  });
});
