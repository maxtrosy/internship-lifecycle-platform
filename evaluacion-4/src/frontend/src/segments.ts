// CR-05 (Evaluación 4) presentation and validation helpers for rotational
// placements. Pure functions so they can be unit-tested without rendering.
import type {
  HoursReviewReason,
  HoursSummary,
  PlacementDossier,
  SegmentGate,
  SegmentInput,
  SegmentModality,
  SegmentStatus,
  WorkRecognition,
} from "./api";

export const SEGMENT_STATUS_LABELS: Record<SegmentStatus, string> = {
  PLANNED: "Planificado",
  ACTIVE: "Activo",
  COMPLETED: "Completado",
  TERMINATED_EARLY: "Terminado anticipadamente",
  TRANSFERRED: "Transferido",
  CANCELLED: "Cancelado",
};

export const SEGMENT_ORIGIN_LABELS: Record<string, string> = {
  PLACEMENT_ACTIVATION: "Creado al activar la práctica",
  MIGRATED_SINGLE: "Migrado desde Evaluación 3",
  ROTATION: "Rotación planificada",
  TRANSFER: "Destino de transferencia",
};

export const MODALITY_LABELS: Record<SegmentModality, string> = {
  ONSITE: "Presencial",
  REMOTE: "Remota",
  HYBRID: "Híbrida",
};

export const RECOGNITION_LABELS: Record<WorkRecognition, string> = {
  ACCEPTED_HOURS_RECOGNIZED: "Horas aceptadas reconocidas",
  NOT_RECOGNIZED: "Trabajo no reconocido",
};

export const HOURS_REVIEW_LABELS: Record<string, string> = {
  SUBMITTED: "Pendiente de revisión",
  ACCEPTED: "Aceptadas",
  REJECTED: "Rechazadas",
  DISPUTED: "En disputa",
};

export const HOURS_REASON_LABELS: Record<HoursReviewReason, string> = {
  DUPLICATE: "Registro duplicado",
  OUTSIDE_SEGMENT: "Fuera del periodo o segmento",
  NOT_VERIFIABLE: "No verificable",
  OTHER: "Otro motivo",
};

export function segmentTone(status: string): string {
  if (status === "ACTIVE" || status === "COMPLETED" || status === "ACCEPTED" || status === "SATISFIED") return "ACTIVE";
  if (status === "CANCELLED" || status === "REJECTED") return "REJECTED";
  return status;
}

export function numeric(value: number | string | null | undefined): number {
  if (value === null || value === undefined) return 0;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function formatHours(value: number | string | null | undefined): string {
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 }).format(numeric(value));
}

/** Reported vs accepted vs pending, never mixing the two (CR-05-BR-04). */
export function hoursOverview(summary: HoursSummary | null | undefined): {
  reported: number; accepted: number; pending: number; pendingEntries: number | null;
} | null {
  if (!summary) return null;
  return {
    reported: numeric(summary.reported_total),
    accepted: numeric(summary.accepted_total),
    pending: summary.segments.reduce((total, row) => total + numeric(row.pending), 0),
    pendingEntries: summary.pending_entries,
  };
}

/** Human-readable segment-level closure blockers (BR-07), from the persisted gate. */
export function segmentGateBlockers(gate: SegmentGate | null | undefined, allowSingleActive = true): string[] {
  if (!gate) return [];
  const blockers: string[] = [];
  let open = gate.open_segments;
  if (allowSingleActive && gate.effective_segments === 1 && gate.active_segments === 1) open -= 1;
  if (open > 0) blockers.push(`${open} segmento(s) planificado(s) o activo(s) sin cerrar`);
  if (gate.pending_hour_entries > 0) blockers.push(`${gate.pending_hour_entries} registro(s) de horas sin revisar`);
  if (gate.segments_missing_final_evaluation.length) {
    blockers.push(`evaluación final pendiente en segmento(s) ${gate.segments_missing_final_evaluation.join(", ")}`);
  }
  if (gate.combined_review_required && !gate.combined_review_approved) {
    blockers.push("revisión académica de la experiencia combinada pendiente");
  }
  return blockers;
}

export function hasSegmentRotation(dossier: PlacementDossier): boolean {
  return (dossier.segments ?? []).filter((segment) => segment.status !== "CANCELLED").length > 1;
}

export type SegmentDraft = {
  host_org_id: string;
  workplace_supervisor_id: string;
  unit: string;
  start_date: string;
  end_date: string;
  modality: string;
  responsibilities: string;
  expected_hours: string;
};

export const EMPTY_SEGMENT_DRAFT: SegmentDraft = {
  host_org_id: "", workplace_supervisor_id: "", unit: "", start_date: "", end_date: "",
  modality: "", responsibilities: "", expected_hours: "",
};

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function buildSegmentInput(draft: SegmentDraft): { value: SegmentInput } | { error: string } {
  const org = Number(draft.host_org_id);
  const supervisor = Number(draft.workplace_supervisor_id);
  if (!Number.isInteger(org) || org <= 0) return { error: "Selecciona la organización del segmento." };
  if (!Number.isInteger(supervisor) || supervisor <= 0) return { error: "Selecciona el supervisor laboral del segmento." };
  if (!draft.unit.trim()) return { error: "Indica la unidad o área del segmento." };
  if (!ISO_DATE.test(draft.start_date) || !ISO_DATE.test(draft.end_date)) return { error: "Indica las fechas de inicio y fin." };
  if (draft.end_date < draft.start_date) return { error: "La fecha de fin debe ser igual o posterior a la de inicio." };
  if (!(draft.modality in MODALITY_LABELS)) return { error: "Selecciona la modalidad." };
  if (!draft.responsibilities.trim()) return { error: "Describe las responsabilidades del segmento." };
  let expected: number | null = null;
  if (draft.expected_hours.trim()) {
    expected = Number(draft.expected_hours);
    if (!Number.isFinite(expected) || expected <= 0) return { error: "Las horas esperadas deben ser mayores que cero." };
  }
  return {
    value: {
      host_org_id: org,
      workplace_supervisor_id: supervisor,
      unit: draft.unit.trim(),
      start_date: draft.start_date,
      end_date: draft.end_date,
      modality: draft.modality as SegmentModality,
      responsibilities: draft.responsibilities.trim(),
      expected_hours: expected,
    },
  };
}

export type HoursReviewDraft = {
  decision: "ACCEPTED" | "REJECTED" | "DISPUTED";
  accepted_hours: string;
  reason_code: "" | HoursReviewReason;
  reason: string;
};

export function buildHoursReview(draft: HoursReviewDraft, reported: number | string):
  { value: { decision: HoursReviewDraft["decision"]; accepted_hours?: number; reason_code?: HoursReviewReason; reason?: string } }
  | { error: string } {
  const value: { decision: HoursReviewDraft["decision"]; accepted_hours?: number; reason_code?: HoursReviewReason; reason?: string } = {
    decision: draft.decision,
  };
  if (draft.decision === "ACCEPTED" && draft.accepted_hours.trim()) {
    const accepted = Number(draft.accepted_hours);
    if (!Number.isFinite(accepted) || accepted <= 0 || accepted > numeric(reported)) {
      return { error: "Las horas aceptadas deben ser mayores que cero y no superar las reportadas." };
    }
    value.accepted_hours = accepted;
  }
  if (draft.decision !== "ACCEPTED" && !draft.reason.trim()) {
    return { error: "Explica el motivo del rechazo o la disputa." };
  }
  if (draft.reason_code) value.reason_code = draft.reason_code;
  if (draft.reason.trim()) value.reason = draft.reason.trim();
  return { value };
}

export function todayIso(now: Date = new Date()): string {
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}
