import { describe, it, expect } from "vitest";
import type { Finding } from "@/lib/api-types";
import { filterFindings, DEFAULT_FINDING_FILTERS } from "@/lib/finding-filters";

const sample: Finding[] = [
  {
    id: "1",
    organization_id: "o",
    project_id: "p",
    scan_job_id: "s",
    source_tool: "zap",
    source_rule_id: null,
    title: "Missing CSP",
    description: null,
    affected_url: "https://example.com/",
    severity: "high",
    confidence: "high",
    correlation_key: null,
    risk_score: 80,
    cvss_score: 7.5,
    source_tools: ["zap"],
    verification_status: "verified",
    verification_notes: null,
    evidence: null,
    status: "open",
    remediation: null,
    risk_explanation: null,
    remediation_steps: null,
    config_file_paths: null,
    config_snippet: null,
    reviewer_notes: null,
    ai_summary: null,
    ai_remediation: null,
    ai_confidence_label: null,
    risk_breakdown: null,
    risk_model_version: null,
    asset_type: "url",
    platform: null,
    masvs_category: null,
    affected_component: null,
    mobile_application_id: null,
    first_seen_at: "2026-01-01",
    last_seen_at: "2026-01-02",
    created_at: "2026-01-01",
    updated_at: "2026-01-02",
  },
  {
    id: "2",
    organization_id: "o",
    project_id: "p",
    scan_job_id: "s",
    source_tool: "passive_http",
    source_rule_id: null,
    title: "Info header",
    description: null,
    affected_url: null,
    severity: "info",
    confidence: "low",
    correlation_key: null,
    risk_score: 10,
    cvss_score: null,
    source_tools: null,
    verification_status: "unverified",
    verification_notes: null,
    evidence: null,
    status: "false_positive",
    remediation: null,
    risk_explanation: null,
    remediation_steps: null,
    config_file_paths: null,
    config_snippet: null,
    reviewer_notes: null,
    ai_summary: null,
    ai_remediation: null,
    ai_confidence_label: null,
    risk_breakdown: null,
    risk_model_version: null,
    asset_type: "url",
    platform: null,
    masvs_category: null,
    affected_component: null,
    mobile_application_id: null,
    first_seen_at: "2026-01-01",
    last_seen_at: "2026-01-02",
    created_at: "2026-01-01",
    updated_at: "2026-01-02",
  },
];

describe("filterFindings", () => {
  it("filters by severity", () => {
    const result = filterFindings(sample, { ...DEFAULT_FINDING_FILTERS, severity: "high" });
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe("1");
  });

  it("filters by search query", () => {
    const result = filterFindings(sample, { ...DEFAULT_FINDING_FILTERS, query: "csp" });
    expect(result).toHaveLength(1);
  });
});
