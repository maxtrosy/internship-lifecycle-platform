const HISTORY_ACTION_LABELS: Record<string, string> = {
  "application.submitted": "Postulación enviada",
  "application.selected": "Selección del empleador registrada",
  "placement.academic_approved": "Aprobación académica registrada",
  "placement.academic_rejected": "Rechazo académico registrado",
  "placement.activated": "Práctica activada",
  "placement.completed": "Finalización confirmada",
  "placement.closed": "Práctica cerrada",
  "placement.change_proposed": "Cambio de datos propuesto",
  "placement.version_approved": "Cambio de datos aprobado",
  "progress.hours_recorded": "Horas registradas",
  "progress.report_submitted": "Avance de práctica registrado",
  "work_plan.activity_assigned": "Actividad asignada al plan de trabajo",
  "evaluation.submitted": "Evaluación registrada",
  "placement.incident_reported": "Situación de práctica reportada",
  "placement.change_reported": "Cambio de práctica reportado",
  "completion_evidence.submitted": "Evidencia final entregada",
  "checklist_item.submitted": "Documento entregado",
  "checklist_item.approved": "Documento aprobado",
  "checklist_item.rejected": "Documento devuelto para corrección",
  "checklist_item.rejected_after_activation": "Requisito documental devuelto para corrección",
};

export function formatHistoryAction(action: unknown): string {
  if (typeof action !== "string") return "Actualización registrada";
  return HISTORY_ACTION_LABELS[action] ?? "Actualización registrada";
}

export function formatHistoryDate(value: unknown): string {
  if (typeof value !== "string") return "Fecha no disponible";
  const timestamp = new Date(value);
  if (!Number.isFinite(timestamp.getTime())) return "Fecha no disponible";
  return timestamp.toLocaleString("es-CO");
}

/**
 * Formats a calendar date ("YYYY-MM-DD", optionally followed by a time part
 * that is ignored) as a local date without any time-zone conversion.
 * `new Date("2026-09-01")` is parsed as UTC midnight, which renders as the
 * previous day in negative-offset zones; this helper avoids that shift.
 */
export function formatCalendarDate(value: unknown, fallback = "Fecha no disponible"): string {
  if (typeof value !== "string") return fallback;
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!match) return fallback;
  const [year, month, day] = match.slice(1).map(Number);
  const date = new Date(year, month - 1, day);
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return fallback;
  return date.toLocaleDateString("es-CO");
}
