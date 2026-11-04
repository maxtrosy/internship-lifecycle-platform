import { describe, expect, it } from "vitest";
import { completionRequirementsSatisfied } from "./completion";

describe("completion gate presentation", () => {
  it("does not treat an unconfigured or unavailable policy as satisfied", () => {
    expect(completionRequirementsSatisfied(false, [])).toBe(false);
    expect(completionRequirementsSatisfied(true, null)).toBe(false);
  });

  it("uses persisted mandatory satisfaction and ignores optional unmet items", () => {
    expect(completionRequirementsSatisfied(true, [
      { kind: "MIN_HOURS", mandatory: true, satisfied: false, threshold: 100 },
    ])).toBe(false);
    expect(completionRequirementsSatisfied(true, [
      { kind: "OPTIONAL_REPORT", mandatory: false, satisfied: false, threshold: null },
    ])).toBe(true);
    expect(completionRequirementsSatisfied(true, [])).toBe(true);
  });
});
