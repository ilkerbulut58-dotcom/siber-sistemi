/** Map raw scan error_log to user-safe messages (no stack traces or internals). */

const INTERNAL_PATTERNS = [
  /traceback/i,
  /redis/i,
  /celery/i,
  /sqlalchemy/i,
  /postgresql/i,
  /\.py:\d+/i,
  /container/i,
  /\/app\//i,
  /exception/i,
];

export function sanitizeScanError(raw: string | null | undefined): {
  titleKey: "scanResults.scanFailed";
  detailKey: string;
  scanId?: string;
} {
  if (!raw || !raw.trim()) {
    return { titleKey: "scanResults.scanFailed", detailKey: "scanResults.errorGeneric" };
  }
  const text = raw.trim();
  if (INTERNAL_PATTERNS.some((p) => p.test(text))) {
    return { titleKey: "scanResults.scanFailed", detailKey: "scanResults.errorInternal" };
  }
  if (/timeout/i.test(text)) {
    return { titleKey: "scanResults.scanFailed", detailKey: "scanResults.errorTimeout" };
  }
  if (/quota|rate.?limit/i.test(text)) {
    return { titleKey: "scanResults.scanFailed", detailKey: "scanResults.errorQuota" };
  }
  if (/domain|verif/i.test(text)) {
    return { titleKey: "scanResults.scanFailed", detailKey: "scanResults.errorDomain" };
  }
  return { titleKey: "scanResults.scanFailed", detailKey: "scanResults.errorGeneric" };
}
