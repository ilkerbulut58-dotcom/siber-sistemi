import type { Finding } from "@/lib/api-types";

export function baseFinding(overrides: Partial<Finding> = {}): Finding {
  return {
    id: "1",
    organization_id: "o",
    project_id: "p",
    scan_job_id: "s",
    source_tool: "passive_http",
    source_rule_id: null,
    title: "Test",
    description: null,
    affected_url: "https://example.com",
    severity: "medium",
    confidence: "medium",
    correlation_key: null,
    risk_score: 50,
    cvss_score: null,
    source_tools: ["passive_http"],
    verification_status: null,
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
    asset_type: "web",
    platform: null,
    masvs_category: null,
    affected_component: null,
    mobile_application_id: null,
    first_seen_at: "",
    last_seen_at: "",
    created_at: "",
    updated_at: "",
    ...overrides,
  };
}

export const sampleRiskBreakdown = {
  total: 55,
  items: [
    {
      key: "severity",
      label: "Önem derecesi",
      value: "55/100 taban",
      weight: 0.55,
      description: "medium seviyesi temel risk katkısı sağlar.",
    },
  ],
};
