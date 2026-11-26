import { afterEach, describe, expect, it, vi } from "vitest";
import type { ChecklistItem, PlacementSegment } from "./api";
import { getRotationReports, updatePlacementSegment } from "./api";
import { buildSegmentUpdate, requirementLabel, revisionValue, segmentEditDraft } from "./segments";

const segment = (patch: Partial<PlacementSegment> = {}): PlacementSegment => ({
  id: 3, sequence_no: 2, host_org_id: 2, host_org_name: "Org Beta", unit: "Laboratorio",
  workplace_supervisor_id: 9, workplace_supervisor_name: "Supervisora", start_date: "2026-12-01", end_date: "2027-01-31",
  modality: "HYBRID", responsibilities: "Apoyo", expected_hours: "60.00", origin: "ROTATION", status: "PLANNED",
  activated_at: null, ended_on: null, ended_at: null, end_reason_shared: null, work_recognition: null,
  recognition_note: null, conditions: [], status_history: [], ...patch,
});

describe("segment adjustments (0019)", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends only the changed fields with the shared reason", () => {
    const planned = segment();
    const draft = { ...segmentEditDraft(planned), unit: " Taller ", workplace_supervisor_id: "12", reason_shared: " Cambio " };
    expect(buildSegmentUpdate(planned, draft)).toEqual({ value: { reason_shared: "Cambio", unit: "Taller", workplace_supervisor_id: 12 } });
    expect(buildSegmentUpdate(planned, { ...segmentEditDraft(planned), reason_shared: "x" })).toEqual({ error: "No hay cambios que guardar." });
    expect(buildSegmentUpdate(planned, { ...segmentEditDraft(planned), modality: "REMOTE", reason_shared: "" }))
      .toEqual({ error: "Indica el motivo visible del ajuste." });
    expect("error" in buildSegmentUpdate(planned, { ...segmentEditDraft(planned), expected_hours: "-1", reason_shared: "x" })).toBe(true);
  });

  it("never sends unit or supervisor for an active segment", () => {
    const active = segment({ status: "ACTIVE" });
    const draft = { ...segmentEditDraft(active), unit: "Otra", workplace_supervisor_id: "12", modality: "REMOTE", expected_hours: "80", reason_shared: "Ajuste" };
    expect(buildSegmentUpdate(active, draft)).toEqual({ value: { reason_shared: "Ajuste", modality: "REMOTE", expected_hours: 80 } });
  });

  it("labels segment evidence with its condition and segment", () => {
    const format = (value: string) => (value === "DOC_INSURANCE" ? "Seguro" : value);
    const plain: ChecklistItem = { id: 1, kind: "DOC_INSURANCE", mandatory: true, status: "REQUIRED" };
    const evidence: ChecklistItem = { ...plain, id: 2, kind: "DOC_SEG2_INSURANCE", mandatory: false, segment_condition_id: 5, condition_kind: "DOC_INSURANCE", segment_sequence_no: 2 };
    expect(requirementLabel(plain, format)).toBe("Seguro");
    expect(requirementLabel(evidence, format)).toBe("Seguro · segmento 2");
    expect(revisionValue("modality", "REMOTE")).toBe("Remota");
    expect(revisionValue("unit", null)).toBe("sin dato");
  });

  it("calls PATCH for adjustments and passes the report state filter", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);
    await updatePlacementSegment(7, 3, { modality: "REMOTE", reason_shared: "Ajuste" });
    await getRotationReports({ organization_id: 2, placement_state: "ACTIVE" });
    const [patch, report] = fetchMock.mock.calls;
    expect(patch[0]).toBe("/placements/7/segments/3");
    expect(patch[1].method).toBe("PATCH");
    expect(JSON.parse(patch[1].body)).toEqual({ modality: "REMOTE", reason_shared: "Ajuste" });
    expect(report[0]).toBe("/reports/rotations?organization_id=2&placement_state=ACTIVE");
  });
});
