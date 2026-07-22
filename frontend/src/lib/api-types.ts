/** Shared API entity types (mirrors backend FindingResponse). */

export interface RiskBreakdownItem {
  key: string;
  label: string;
  value: string;
  weight: number;
  description: string;
}

export interface RiskBreakdown {
  total: number;
  items: RiskBreakdownItem[];
}

export interface Finding {
  id: string;
  organization_id: string;
  project_id: string;
  scan_job_id: string | null;
  source_tool: string;
  source_rule_id: string | null;
  title: string;
  description: string | null;
  affected_url: string | null;
  severity: "critical" | "high" | "medium" | "low" | "info";
  confidence: string | null;
  correlation_key: string | null;
  risk_score: number | null;
  cvss_score: number | null;
  source_tools: string[] | null;
  verification_status: string | null;
  verification_notes: string | null;
  evidence: Record<string, unknown> | null;
  status: "open" | "resolved" | "false_positive" | "accepted_risk" | "inconclusive";
  remediation: string | null;
  risk_explanation: string | null;
  remediation_steps: string[] | null;
  config_file_paths: string[] | null;
  config_snippet: string | null;
  reviewer_notes: string | null;
  ai_summary: string | null;
  ai_remediation: string | null;
  ai_confidence_label: string | null;
  risk_breakdown: RiskBreakdown | null;
  risk_model_version: string | null;
  asset_type: string;
  platform: string | null;
  masvs_category: string | null;
  affected_component: string | null;
  mobile_application_id: string | null;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
}

export interface BenchmarkRun {
  id: string;
  benchmark_target_id: string;
  scan_id: string | null;
  mobile_application_id: string | null;
  git_commit: string | null;
  scan_profile: string | null;
  fixture_set: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  error_log: string | null;
}

export interface QualitySummary {
  precision: number;
  recall: number;
  f1_score: number;
  false_positive_rate: number;
  false_negative_rate: number;
  average_duration_seconds: number;
  expected_count: number;
  true_positive_count: number;
  false_negative_count: number;
  false_positive_count: number;
  duplicate_count: number;
  scanner_error_count: number;
  last_run: BenchmarkRun | null;
  by_target_type: Record<string, { runs: number; precision: number; recall: number; f1_score: number }>;
  scanner_health: { failed_runs?: number; status?: string };
  baseline_delta: Record<string, unknown> | null;
}

export interface FindingHistoryEntry {
  id: string;
  finding_id: string;
  scan_job_id: string | null;
  event_type: "detected" | "redetected" | "reopened" | "status_change" | "retest_started";
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface FindingUpdate {
  status?: string;
  reviewer_notes?: string;
}

export interface ScanJob {
  id: string;
  organization_id: string;
  project_id: string;
  domain_id: string;
  initiated_by?: string;
  scan_profile: string;
  target_url: string;
  status: string;
  findings_count: number;
  error_log: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at?: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  owner_id: string;
  is_active: boolean;
  is_managed_workspace: boolean;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  environment: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Domain {
  id: string;
  project_id: string;
  organization_id: string;
  hostname: string;
  is_verified: boolean;
  verified_at: string | null;
  last_checked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface VerificationInstructions {
  domain_id: string;
  hostname: string;
  method: string;
  token: string;
  expires_at: string;
  instructions: string[];
}

export interface ScanProfile {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  is_active: boolean;
}

export interface QuickScanResult {
  organization_id: string;
  project_id: string;
  domain_id: string;
  scan: ScanJob;
}

export interface Asset {
  id: string;
  organization_id: string;
  project_id: string;
  domain_id: string;
  discovery_job_id: string | null;
  parent_asset_id: string | null;
  asset_type: string;
  identifier: string;
  url: string | null;
  status: string;
  metadata: Record<string, unknown> | null;
  exposure_score: number;
  risk_score: number | null;
  first_seen_at: string;
  last_seen_at: string;
  last_scanned_at: string | null;
}

export interface AsmDiscoveryJob {
  id: string;
  organization_id: string;
  project_id: string;
  domain_id: string;
  target_url: string;
  status: string;
  assets_count: number;
  summary: Record<string, unknown> | null;
  error_log: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface AttackSurfaceSummary {
  total_assets: number;
  subdomains: number;
  ip_addresses: number;
  technologies: { name: string; category?: string }[];
  cdn_waf: { name: string; type?: string }[];
  dns_records: Record<string, string[]>;
  avg_risk_score: number | null;
  max_risk_score: number | null;
  last_discovery_at: string | null;
  last_discovery_status: string | null;
}

export interface MobileApplication {
  id: string;
  organization_id: string;
  project_id: string;
  platform: string;
  application_name: string | null;
  package_name: string | null;
  version_name: string | null;
  version_code: string | null;
  environment: string;
  original_filename: string;
  file_size: number;
  sha256: string;
  upload_status: string;
  analysis_status: string;
  security_score: number | null;
  findings_count: number;
  analysis_summary: Record<string, unknown> | null;
  error_log: string | null;
  created_by: string;
  analyzed_at: string | null;
  created_at: string;
  updated_at: string;
}

export type MobileUploadResult = MobileApplication & {
  duplicate: boolean;
};

export interface SensitiveDataSummary {
  password_findings: number;
  bank_findings: number;
  payment_findings: number;
  other_secrets: number;
  note: string;
}

export interface SiteProfile {
  id: string;
  organization_id: string;
  project_id: string;
  scan_job_id: string;
  target_url: string;
  hostname: string;
  profile: Record<string, unknown>;
  sensitive_data: SensitiveDataSummary;
  collected_at: string;
}

export interface SupportGrant {
  id: string;
  organization_id: string;
  organization_name: string | null;
  granted_to_user_id: string;
  granted_to_email: string | null;
  granted_by_user_id: string;
  reason: string;
  expires_at: string;
  revoked_at: string | null;
  created_at: string;
  is_active: boolean;
}
