/** Mask sensitive evidence before display (mirrors backend data_masker.py). */

const JWT_PATTERN = /eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g;
const API_KEY_PATTERN =
  /(api[_-]?key|secret|password|token|authorization)\s*[:=]\s*\S+/gi;

const SENSITIVE_HEADER_NAMES = new Set([
  "authorization",
  "cookie",
  "set-cookie",
  "x-api-key",
  "x-auth-token",
]);

const MAX_TEXT = 4000;
const MAX_EVIDENCE = 1500;

function redactText(value: string): string {
  let text = value.replace(JWT_PATTERN, "[REDACTED_JWT]");
  text = text.replace(API_KEY_PATTERN, "$1=[REDACTED]");
  if (text.length > MAX_TEXT) {
    return `${text.slice(0, MAX_TEXT)}…[truncated]`;
  }
  return text;
}

export function maskText(value: string | null | undefined): string | null {
  if (value == null || value === "") return null;
  return redactText(value);
}

export function maskEvidenceValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "string") return redactText(value);
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    return value.map((v) => maskEvidenceValue(v)).join(", ");
  }
  if (typeof value === "object") {
    return redactText(JSON.stringify(value, null, 2));
  }
  return redactText(String(value));
}

export function formatMaskedEvidence(
  evidence: Record<string, unknown> | null | undefined
): { label: string; value: string }[] {
  if (!evidence || Object.keys(evidence).length === 0) return [];

  const rows: { label: string; value: string }[] = [];
  const headers = evidence.headers;

  if (headers && typeof headers === "object" && !Array.isArray(headers)) {
    for (const [name, headerValue] of Object.entries(headers as Record<string, unknown>)) {
      const lower = name.toLowerCase();
      rows.push({
        label: `Header: ${name}`,
        value: SENSITIVE_HEADER_NAMES.has(lower)
          ? "[REDACTED]"
          : redactText(String(headerValue)),
      });
    }
  }

  const skip = new Set(["headers"]);
  for (const [key, val] of Object.entries(evidence)) {
    if (skip.has(key)) continue;
    const lower = key.toLowerCase();
    if (SENSITIVE_HEADER_NAMES.has(lower)) {
      rows.push({ label: key, value: "[REDACTED]" });
      continue;
    }
    if (key === "cookie_sample") {
      rows.push({ label: "Cookie örneği", value: "[REDACTED]" });
      continue;
    }
    rows.push({ label: key, value: maskEvidenceValue(val) });
  }

  const total = rows.reduce((n, r) => n + r.value.length, 0);
  if (total > MAX_EVIDENCE) {
    return rows.map((r) => ({
      ...r,
      value: r.value.length > 200 ? `${r.value.slice(0, 200)}…` : r.value,
    }));
  }
  return rows;
}
