import { afterEach, describe, expect, it, vi } from "vitest";
import {
  activatePlacementSegment, confirmSegmentCondition, createPlacementSegment, recordExperienceReview,
  recordPlacementHours, reviewPlacementHours, terminatePlacementSegment, transferPlacementSegment,
} from "./api";

const destination = {
  host_org_id: 2, workplace_supervisor_id: 9, unit: "Laboratorio", start_date: "2026-12-01", end_date: "2027-01-31",
  modality: "HYBRID" as const, responsibilities: "Apoyo", expected_hours: null,
};

describe("CR-05 segment API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("calls the segment, transfer, review and combined-review endpoints", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 201, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    await createPlacementSegment(7, destination);
    await confirmSegmentCondition(7, 3, 11, "Póliza POL-1");
    await activatePlacementSegment(7, 3);
    await transferPlacementSegment(7, 3, { effective_date: "2026-11-20", reason_shared: "Rotación",
      prior_work_treatment: "ACCEPTED_HOURS_RECOGNIZED", destination });
    await terminatePlacementSegment(7, 4, { ended_on: "2026-11-20", reason_shared: "Suspensión",
      work_recognition: "NOT_RECOGNIZED" });
    await reviewPlacementHours(7, 21, { decision: "ACCEPTED", accepted_hours: 6 });
    await recordExperienceReview(7, "APPROVED", "Cumple");

    const urls = fetchMock.mock.calls.map(([url]) => url);
    expect(urls).toEqual([
      "/placements/7/segments",
      "/placements/7/segments/3/conditions/11/confirm",
      "/placements/7/segments/3/activate",
      "/placements/7/segments/3/transfer",
      "/placements/7/segments/4/terminate",
      "/placements/7/hours/21/review",
      "/placements/7/experience-review",
    ]);
    expect(fetchMock.mock.calls.every(([, init]) => init.method === "POST" && init.credentials === "same-origin")).toBe(true);
    expect(JSON.parse(fetchMock.mock.calls[5][1].body)).toEqual({ decision: "ACCEPTED", accepted_hours: 6 });
  });

  it("sends optional work date and description only when present", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);
    await recordPlacementHours(7, 4.5);
    await recordPlacementHours(7, 8, { work_date: "2026-11-19", description: " Jornada " });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ hours: 4.5 });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ hours: 8, work_date: "2026-11-19", description: "Jornada" });
  });

  it("presents CR-05 domain errors in Spanish", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ error: "SEGMENT_ALREADY_ACTIVE" }) }));
    await expect(activatePlacementSegment(7, 3)).rejects.toThrow("Ya existe un segmento activo");
  });
});
