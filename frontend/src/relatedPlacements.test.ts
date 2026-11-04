import { describe, expect, it } from "vitest";
import { getRelatedPlacementsState } from "./relatedPlacements";

const placement = {
  id: 7, state: "ACTIVE", application_state: "SELECTED", opportunity_title: "Práctica",
  opportunity_state: "PUBLISHED", host_org_name: "Organización", program_code: "ING-SIS",
  start_date: null, end_date: null,
};

describe("relationship-scoped dashboard list state", () => {
  it("distinguishes loading, error, empty and populated results", () => {
    expect(getRelatedPlacementsState(null, true, false)).toBe("loading");
    expect(getRelatedPlacementsState(null, false, true)).toBe("error");
    expect(getRelatedPlacementsState([], false, false)).toBe("empty");
    expect(getRelatedPlacementsState([placement], false, false)).toBe("ready");
  });

  it("keeps a loading response from appearing successful before it settles", () => {
    expect(getRelatedPlacementsState([], true, false)).toBe("loading");
    expect(getRelatedPlacementsState(null, false, false)).toBe("loading");
  });
});
