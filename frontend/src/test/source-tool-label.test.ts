import { describe, expect, it } from "vitest";
import { sourceToolLabel } from "@/lib/i18n";
import { formatSourceTool } from "@/lib/scan-analytics";

describe("sourceToolLabel", () => {
  it("labels known tools in Turkish", () => {
    expect(sourceToolLabel("tr", "passive_http")).toBe("HTTP Kontrolleri");
  });

  it("falls back to raw tool name when unmapped", () => {
    expect(sourceToolLabel("tr", "unknown_scanner")).toBe("unknown_scanner");
  });

  it("does not throw for invalid locale", () => {
    expect(sourceToolLabel("en" as "tr", "passive_http")).toBe("HTTP Kontrolleri");
  });

  it("does not throw when locale and tool args look swapped", () => {
    expect(sourceToolLabel("passive_http" as "tr", "de")).toBe("de");
  });
});

describe("formatSourceTool", () => {
  it("ignores numeric map index when used as map callback", () => {
    expect(["passive_http", "nuclei"].map(formatSourceTool)).toEqual([
      "HTTP Kontrolleri",
      "Nuclei",
    ]);
  });
});
