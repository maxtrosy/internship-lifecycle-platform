import { describe, expect, it } from "vitest";
import { formatCalendarDate, formatHistoryAction, formatHistoryDate } from "./history";

describe("placement history presentation", () => {
  it("translates known actions to student-facing text", () => {
    expect(formatHistoryAction("application.submitted")).toBe("Postulación enviada");
    expect(formatHistoryAction("application.selected")).toBe("Selección del empleador registrada");
    expect(formatHistoryAction("placement.activated")).toBe("Práctica activada");
    expect(formatHistoryAction("progress.hours_recorded")).toBe("Horas registradas");
    expect(formatHistoryAction("progress.report_submitted")).toBe("Avance de práctica registrado");
    expect(formatHistoryAction("work_plan.activity_assigned")).toBe("Actividad asignada al plan de trabajo");
    expect(formatHistoryAction("evaluation.submitted")).toBe("Evaluación registrada");
    expect(formatHistoryAction("placement.change_reported")).toBe("Cambio de práctica reportado");
    expect(formatHistoryAction("completion_evidence.submitted")).toBe("Evidencia final entregada");
    expect(formatHistoryAction("checklist_item.rejected")).toBe("Documento devuelto para corrección");
  });

  it("does not expose unknown or malformed internal action values", () => {
    expect(formatHistoryAction("internal.future_action")).toBe("Actualización registrada");
    expect(formatHistoryAction({ technical: true })).toBe("Actualización registrada");
    expect(formatHistoryAction(null)).toBe("Actualización registrada");
  });

  it("formats valid dates and handles incomplete data", () => {
    expect(formatHistoryDate("2026-10-25T12:00:00Z")).not.toBe("Fecha no disponible");
    expect(formatHistoryDate("not-a-date")).toBe("Fecha no disponible");
    expect(formatHistoryDate(null)).toBe("Fecha no disponible");
  });

  it("formats calendar dates without shifting the day or adding a time", () => {
    const expected = new Date(2026, 8, 1).toLocaleDateString("es-CO");
    expect(formatCalendarDate("2026-09-01")).toBe(expected);
    expect(formatCalendarDate("2026-09-01T00:00:00Z")).toBe(expected);
    expect(formatCalendarDate("2026-09-01")).not.toMatch(/:/);
    expect(formatCalendarDate("2026-02-30")).toBe("Fecha no disponible");
    expect(formatCalendarDate("01/09/2026")).toBe("Fecha no disponible");
    expect(formatCalendarDate(undefined, "—")).toBe("—");
  });
});
