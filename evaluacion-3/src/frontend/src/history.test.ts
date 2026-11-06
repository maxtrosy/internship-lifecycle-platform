import { describe, expect, it } from "vitest";
import { formatHistoryAction, formatHistoryDate } from "./history";

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
});
