/** Resolve API base URL for browser vs server. */
export function getApiBase(): string {
  if (typeof window !== "undefined") {
    // Same host reverse-proxies /api/v1 — avoids broken baked-in localhost URLs.
    return "";
  }
  return (
    process.env.API_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000"
  );
}
