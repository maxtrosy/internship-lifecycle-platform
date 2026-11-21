import { describe, expect, it } from "vitest";
import type { HoursSummary, SegmentGate } from "./api";
import { EMPTY_SEGMENT_DRAFT, buildHoursReview, buildSegmentInput, hoursOverview, segmentGateBlockers, todayIso } from "./segments";

const gate = (patch: Partial<SegmentGate> = {}): SegmentGate => ({
  open_segments: 0, active_segments: 0, effective_segments: 1, pending_hour_entries: 0,
  segments_missing_final_evaluation: [], combined_review_required: false, combined_review_approved: true, ...patch,
});

describe("CR-05 segment helpers", () => {
  it("keeps reported, accepted and pending hours separate (BR-04)", () => {
    const summary: HoursSummary = {
      scope: "PLACEMENT", reported_total: "110", accepted_total: "90", pending_entries: 1,
      segments: [
        { segment_id: 1, sequence_no: 1, work_recognition: "ACCEPTED_HOURS_RECOGNIZED", reported: "60", pending: "0", accepted: "50", rejected: "10", disputed: "0", counts_toward_total: true },
        { segment_id: 2, sequence_no: 2, work_recognition: null, reported: "50", pending: "10", accepted: "40", rejected: "0", disputed: "0", counts_toward_total: true },
      ],
    };
    expect(hoursOverview(summary)).toEqual({ reported: 110, accepted: 90, pending: 10, pendingEntries: 1 });
    expect(hoursOverview(null)).toBeNull();
  });

  it("explains segment closure blockers and tolerates the single active segment (BR-07/BR-10)", () => {
    expect(segmentGateBlockers(gate({ open_segments: 1, active_segments: 1 }))).toEqual([]);
    expect(segmentGateBlockers(gate({ open_segments: 1, active_segments: 1 }), false)).toHaveLength(1);
    const blockers = segmentGateBlockers(gate({
      open_segments: 1, effective_segments: 2, pending_hour_entries: 2,
      segments_missing_final_evaluation: [2], combined_review_required: true, combined_review_approved: false,
    }));
    expect(blockers).toHaveLength(4);
    expect(blockers.join(" ")).toContain("experiencia combinada");
  });

  it("validates a segment draft before sending it", () => {
    expect(buildSegmentInput(EMPTY_SEGMENT_DRAFT)).toEqual({ error: "Selecciona la organización del segmento." });
    const draft = { host_org_id: "2", workplace_supervisor_id: "9", unit: " Laboratorio ", start_date: "2026-12-01",
      end_date: "2026-11-01", modality: "HYBRID", responsibilities: "Apoyo", expected_hours: "" };
    expect(buildSegmentInput(draft)).toEqual({ error: "La fecha de fin debe ser igual o posterior a la de inicio." });
    expect(buildSegmentInput({ ...draft, end_date: "2027-01-31", expected_hours: "80" })).toEqual({ value: {
      host_org_id: 2, workplace_supervisor_id: 9, unit: "Laboratorio", start_date: "2026-12-01", end_date: "2027-01-31",
      modality: "HYBRID", responsibilities: "Apoyo", expected_hours: 80,
    } });
  });

  it("never accepts more hours than reported and requires a reason to reject", () => {
    expect(buildHoursReview({ decision: "ACCEPTED", accepted_hours: "9", reason_code: "", reason: "" }, "8"))
      .toHaveProperty("error");
    expect(buildHoursReview({ decision: "ACCEPTED", accepted_hours: "6", reason_code: "NOT_VERIFIABLE", reason: "Parcial" }, "8"))
      .toEqual({ value: { decision: "ACCEPTED", accepted_hours: 6, reason_code: "NOT_VERIFIABLE", reason: "Parcial" } });
    expect(buildHoursReview({ decision: "REJECTED", accepted_hours: "", reason_code: "DUPLICATE", reason: " " }, "8"))
      .toHaveProperty("error");
    expect(buildHoursReview({ decision: "ACCEPTED", accepted_hours: "", reason_code: "", reason: "" }, "8"))
      .toEqual({ value: { decision: "ACCEPTED" } });
  });

  it("formats the local date for date inputs", () => {
    expect(todayIso(new Date(2026, 10, 20, 23, 30))).toBe("2026-11-20");
  });
});
