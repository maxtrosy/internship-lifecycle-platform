import { describe, expect, it } from "vitest";
import { hoursFromHistory, totalHours } from "./progress";

describe("work-log history presentation", () => {
  it("shows recorded hour rows and totals them", () => {
    const entries = hoursFromHistory([
      { id: 2, created_at: "2026-10-24T10:00:00Z", hours: 4.5 },
      { id: 1, created_at: "2026-10-23T10:00:00Z", hours: 2 },
      { id: 3, created_at: "2026-10-24T11:00:00Z", hours: 3 },
    ]);

    expect(entries.map((entry) => entry.hours)).toEqual([3, 4.5, 2]);
    expect(totalHours(entries)).toBe(9.5);
  });

  it("returns an empty summary for incomplete or unexpected data", () => {
    expect(hoursFromHistory(null)).toEqual([]);
    expect(hoursFromHistory([{ id: 1, created_at: "today", hours: "8" }])).toEqual([
      { id: 1, occurredAt: "today", hours: 8 },
    ]);
    expect(hoursFromHistory([{ id: 1, created_at: "today", hours: -2 }])).toEqual([]);
  });
});
