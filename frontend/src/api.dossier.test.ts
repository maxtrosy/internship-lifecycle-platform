import { afterEach, describe, expect, it, vi } from "vitest";
import { closePlacement, confirmPlacementCompletion, getPlacementDossier, listVisiblePlacements } from "./api";

describe("placement dossier API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads the relation-scoped practice index using the session cookie", async () => {
    const payload = [{
      id: 12, state: "ACTIVE", application_state: "SELECTED", opportunity_title: "Práctica",
      opportunity_state: "PUBLISHED", host_org_name: "Org Alfa", program_code: "ING-SIS",
      start_date: "2026-11-02", end_date: "2027-02-26",
    }];
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => payload });
    vi.stubGlobal("fetch", fetchMock);

    await expect(listVisiblePlacements()).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith("/placements", expect.objectContaining({ credentials: "same-origin" }));
  });

  it("loads the full persisted dossier from the selected placement resource", async () => {
    const payload = {
      placement: { id: 12, state: "ACTIVE", activation_requirements_instantiated: true, activation_ready: false, activation_unmet: [] },
      application: { id: 20, state: "SELECTED", eligibility_result: "ELIGIBLE", eligibility_policy_version: null },
      opportunity: { id: 3, title: "Práctica", state: "PUBLISHED", host_org_name: "Org Alfa", program_code: "ING-SIS", program_name: "Sistemas" },
      student: { display_name: "Estudiante", program_code: "ING-SIS", program_name: "Sistemas" },
      current_version: null, versions: [], responsibles: { program_coordinators: [], faculty_supervisors: [] },
      activation_requirements: [], completion_requirements: [], completion_requirements_configured: true,
      completion_policy_version: 2, activation_policy_version: 3, documents: [], hours: [], hours_total: 4.5,
      capabilities: { read_documents: true, submit_documents: false, read_hours: true, review_documents: false, decide_academically: false, record_hours: true, activate: false, confirm_completion: false, close_placement: false },
      activity: [{ occurred_at: "2026-10-25T12:00:00Z", action: "application.selected" }],
    };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => payload });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getPlacementDossier(12)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith("/placements/12/dossier", expect.objectContaining({ credentials: "same-origin" }));
  });

  it("sends completion confirmation and closure to their protected lifecycle endpoints", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204 });
    vi.stubGlobal("fetch", fetchMock);

    await confirmPlacementCompletion(12);
    await closePlacement(12);

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/placements/12/confirm-completion", expect.objectContaining({
      method: "POST", credentials: "same-origin",
    }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/placements/12/close", expect.objectContaining({
      method: "POST", credentials: "same-origin",
    }));
  });
});
