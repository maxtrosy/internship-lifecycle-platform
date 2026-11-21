import { describe, expect, it } from "vitest";
import { canDisplayDossierHours } from "./dossier";

describe("persisted hours in the practice dossier", () => {
  it("requires the backend read capability and a projected history", () => {
    expect(canDisplayDossierHours(false, [{ id: 1, created_at: "2026-10-26", hours: 2 }])).toBe(false);
    expect(canDisplayDossierHours(true, null)).toBe(false);
  });

  it("keeps an authorized empty or populated history displayable for any lifecycle state", () => {
    expect(canDisplayDossierHours(true, [])).toBe(true);
    expect(canDisplayDossierHours(true, [{ id: 1, created_at: "2026-10-26", hours: 2 }])).toBe(true);
  });
});
