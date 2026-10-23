import { describe, expect, it } from "vitest";
import { presentEligibility } from "./eligibility";

describe("presentEligibility", () => {
  it("presents an eligible result and available student criteria", () => {
    expect(presentEligibility({
      result: "ELIGIBLE",
      reasons: [],
      inputs: { credits: 105, academic_level: 7 },
    })).toEqual({
      state: "eligible",
      label: "Elegible",
      criteria: [
        { label: "Créditos", value: 105 },
        { label: "Nivel académico", value: 7 },
      ],
      reasons: [],
      hasDetails: true,
    });
  });

  it("recognizes the backend's not-eligible result variant", () => {
    expect(presentEligibility({ result: "NOT_ELIGIBLE", reasons: [] }).label).toBe("No elegible");
    expect(presentEligibility({ result: "INELIGIBLE", reasons: [] }).state).toBe("ineligible");
  });

  it("translates known reasons without changing the reported thresholds", () => {
    expect(presentEligibility({
      result: "NOT_ELIGIBLE",
      reasons: ["credits 90 < 100", "academic_level 5 < 6", "missing prerequisites ['MAT101']"],
    }).reasons).toEqual([
      "Créditos: 90; mínimo exigido: 100.",
      "Nivel académico: 5; mínimo exigido: 6.",
      "Prerrequisitos faltantes: MAT101.",
    ]);
  });

  it("keeps valid results when some criteria or reasons are missing or malformed", () => {
    expect(presentEligibility({
      result: "ELIGIBLE",
      inputs: { credits: null, academic_level: "7" },
      reasons: null,
    })).toEqual({
      state: "eligible",
      label: "Elegible",
      criteria: [],
      reasons: [],
      hasDetails: false,
    });
  });

  it("shows a neutral state for unexpected shapes and ignores non-text reasons", () => {
    expect(presentEligibility("{not valid JSON}").state).toBe("unknown");
    expect(presentEligibility(["ELIGIBLE"]).label).toBe("Estado no disponible");
    expect(presentEligibility({ result: { value: "ELIGIBLE" }, reasons: [{ technical: true }] })).toEqual({
      state: "unknown",
      label: "Estado no disponible",
      criteria: [],
      reasons: [],
      hasDetails: false,
    });
  });
});
