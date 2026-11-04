import { describe, expect, it } from "vitest";
import { getStudentJourney } from "./studentJourney";

const noActivation = undefined;

describe("student journey guidance", () => {
  it("shows a loading state instead of suggesting a misleading next step", () => {
    expect(getStudentJourney(undefined, noActivation, true, false)).toMatchObject({
      title: "Consultando tus procesos",
      disabled: true,
    });
  });

  it("guides an eligible submitted application to its persisted status", () => {
    expect(getStudentJourney({ state: "SUBMITTED", placement_state: null, placement_id: null }, noActivation, false, true)).toMatchObject({
      title: "Tu postulación fue enviada",
      action: "applications",
      state: "SUBMITTED",
    });
  });

  it("does not direct a student to complete requirements owned by another relationship", () => {
    const status = {
      placement_id: 42, state: "DOCUMENTATION_PENDING", activation_requirements_instantiated: true,
      activation_noncompliant: false, ready_to_activate: false, unmet: ["SUPERVISORS_ASSIGNED"],
      items: [{ id: 1, kind: "COND_SUPERVISOR_ASSIGNED", mandatory: true, status: "REQUIRED" }],
    };
    expect(getStudentJourney({ state: "SELECTED", placement_state: "DOCUMENTATION_PENDING", placement_id: 42 }, status, false, true)).toMatchObject({
      title: "Consulta los requisitos de activación",
      action: "documents",
    });
  });

  it("directs a student to document actions only when persisted document statuses support it", () => {
    const status = {
      placement_id: 42, state: "DOCUMENTATION_PENDING", activation_requirements_instantiated: true,
      activation_noncompliant: false, ready_to_activate: false, unmet: ["DOC_INSURANCE"],
      items: [{ id: 1, kind: "DOC_INSURANCE", mandatory: true, status: "REJECTED" }],
    };
    expect(getStudentJourney({ state: "SELECTED", placement_state: "DOCUMENTATION_PENDING", placement_id: 42 }, status, false, true)).toMatchObject({
      title: "Revisa tus documentos",
      actionLabel: "Revisar documentos",
    });
  });

  it("sends an active student to the integrated dossier", () => {
    expect(getStudentJourney({ state: "SELECTED", placement_state: "ACTIVE", placement_id: 42 }, noActivation, false, true)).toMatchObject({
      title: "Tu práctica está activa",
      action: "dossier",
      actionLabel: "Abrir expediente",
    });
  });

  it("keeps completed and closed practices in their read-only history", () => {
    expect(getStudentJourney({ state: "SELECTED", placement_state: "CLOSED", placement_id: 42 }, noActivation, false, true)).toMatchObject({
      title: "La práctica está cerrada",
      action: "dossier",
      actionLabel: "Ver historial",
    });
  });

  it("explains ineligibility without promising another transition", () => {
    expect(getStudentJourney({ state: "INELIGIBLE", placement_state: null, placement_id: null }, noActivation, false, true)).toMatchObject({
      title: "La postulación no cumple la elegibilidad",
      action: "applications",
    });
  });
});
