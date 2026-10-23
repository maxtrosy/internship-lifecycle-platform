import { describe, expect, it } from "vitest";
import { formatDomainLabel } from "./ui";

describe("formatDomainLabel", () => {
  it("preserves readable eligibility badge labels", () => {
    expect(formatDomainLabel("Elegible")).toBe("Elegible");
    expect(formatDomainLabel("No elegible")).toBe("No elegible");
    expect(formatDomainLabel("Estado no disponible")).toBe("Estado no disponible");
  });
});
