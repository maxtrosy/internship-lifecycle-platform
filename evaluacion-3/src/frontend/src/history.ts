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
