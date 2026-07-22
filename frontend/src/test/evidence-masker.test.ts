import { describe, it, expect } from "vitest";
import { formatMaskedEvidence, maskText } from "@/lib/evidence-masker";

describe("evidence-masker", () => {
  it("redacts JWT tokens", () => {
    const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.sig";
    expect(maskText(`Bearer ${token}`)).toContain("[REDACTED_JWT]");
  });

  it("redacts sensitive headers in evidence", () => {
    const rows = formatMaskedEvidence({
      headers: {
        authorization: "Bearer secret",
        "content-type": "text/html",
      },
    });
    expect(rows.find((r) => r.label.includes("authorization"))?.value).toBe("[REDACTED]");
    expect(rows.find((r) => r.label.includes("content-type"))?.value).toBe("text/html");
  });

  it("redacts cookie samples", () => {
    const rows = formatMaskedEvidence({ cookie_sample: "session=abc123" });
    expect(rows[0]?.value).toBe("[REDACTED]");
  });
});
