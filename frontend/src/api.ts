export type User = {
  id: number;
  username: string;
  display_name: string;
  email: string | null;
  roles: { role: string; program_id: number | null; host_org_id: number | null }[];
};

export type Opportunity = {
  id: number;
  host_org_id: number;
  program_id: number;
  title: string;
  state: string;
  program_code: string;
  host_name: string;
  can_submit_for_review?: boolean;
  can_approve_for_publication?: boolean;
  can_publish?: boolean;
  can_close?: boolean;
  review_authority_configured?: boolean;
  publisher_authority_configured?: boolean;
};

export type OpportunityCatalogs = {
  organizations: { id: number; name: string }[];
  programs: { id: number; code: string; name: string }[];
};

export type WorkplaceSupervisor = { id: number; display_name: string };

export type Application = {
  id: number;
  opportunity_id: number;
  state: string;
  // JSONB is intentionally treated as unknown: old and future records may have
  // different shapes, and the UI validates it before presenting anything.
  eligibility_result: unknown;
  title: string;
  placement_id: number | null;
  placement_state: string | null;
};

export type EmployerApplication = {
  id: number;
  opportunity_id: number;
  state: string;
  eligibility_result: unknown;
  display_name: string;
  program_code: string;
  placement_id: number | null;
  placement_state: string | null;
};

export type PendingEligibilityReview = {
  id: number;
  state: "PENDING_ELIGIBILITY_REVIEW";
  eligibility_result: unknown;
  policy_version: number | null;
  display_name: string;
  program_code: string;
  opportunity_title: string;
};

export type PendingAcademic = {
  id: number;
  state: string;
  application_id: number;
  student_id: number;
  display_name: string;
  program_code: string;
  opportunity_title: string;
};

export type ProgressHoursEntry = {
  id: number;
  created_at: string;
  // PostgreSQL Decimal is JSON-encoded as a string by the current API stack.
  hours: number | string;
  placement_version_id?: number | null;
  version_no?: number | null;
  // CR-05: every entry belongs to one segment and has an explicit review state.
  segment_id?: number | null;
  segment_sequence_no?: number | null;
  work_date?: string | null;
  description?: string | null;
  review_status?: HoursReviewStatus;
  accepted_hours?: number | string | null;
  review_reason_code?: HoursReviewReason | null;
  review_reason?: string | null;
  reviewed_at?: string | null;
  reviewed_by?: string | null;
};

export type HoursReviewStatus = "SUBMITTED" | "ACCEPTED" | "REJECTED" | "DISPUTED";
export type HoursReviewReason = "DUPLICATE" | "OUTSIDE_SEGMENT" | "NOT_VERIFIABLE" | "OTHER";
export type SegmentStatus = "PLANNED" | "ACTIVE" | "COMPLETED" | "TERMINATED_EARLY" | "TRANSFERRED" | "CANCELLED";
export type WorkRecognition = "ACCEPTED_HOURS_RECOGNIZED" | "NOT_RECOGNIZED";
export type SegmentModality = "ONSITE" | "REMOTE" | "HYBRID";

export type SegmentCondition = {
  id: number;
  kind: string;
  status: "REQUIRED" | "SATISFIED";
  confirmed_at: string | null;
  reference: string | null;
  confirmed_by: string | null;
};

export type PlacementSegment = {
  id: number;
  sequence_no: number;
  host_org_id: number;
  host_org_name: string;
  unit: string | null;
  workplace_supervisor_id: number | null;
  workplace_supervisor_name: string | null;
  start_date: string;
  end_date: string;
  modality: SegmentModality | null;
  responsibilities: string;
  expected_hours: number | string | null;
  origin: "PLACEMENT_ACTIVATION" | "MIGRATED_SINGLE" | "ROTATION" | "TRANSFER";
  status: SegmentStatus;
  activated_at: string | null;
  ended_on: string | null;
  ended_at: string | null;
  end_reason_shared: string | null;
  // Present only for roles allowed to read confidential reasons (CR-05-BR-09).
  end_reason_internal?: string | null;
  work_recognition: WorkRecognition | null;
  recognition_note: string | null;
  conditions: SegmentCondition[];
  status_history: { from_status: SegmentStatus | null; to_status: SegmentStatus; changed_at: string; actor_name: string | null }[];
  // Append-only period changes (migration 0018); only the shared reason is stored.
  schedule_changes?: SegmentScheduleChange[];
};

export type SegmentScheduleChange = {
  from_start_date: string;
  from_end_date: string;
  to_start_date: string;
  to_end_date: string;
  reason_shared: string;
  changed_at: string;
  actor_name: string | null;
};

export type PlacementTransfer = {
  id: number;
  from_segment_id: number;
  from_sequence_no: number;
  to_segment_id: number;
  to_sequence_no: number;
  effective_date: string;
  reason_shared: string;
  reason_internal?: string | null;
  prior_work_treatment: WorkRecognition;
  approved_at: string;
  approved_by: string;
};

export type HoursSummarySegment = {
  segment_id: number | null;
  sequence_no: number | null;
  work_recognition: WorkRecognition | null;
  reported: number | string;
  pending: number | string;
  accepted: number | string;
  rejected: number | string;
  disputed: number | string;
  counts_toward_total: boolean;
};

export type HoursSummary = {
  segments: HoursSummarySegment[];
  reported_total: number | string;
  accepted_total: number | string;
  pending_entries: number | null;
  scope: "PLACEMENT" | "SEGMENT";
};

export type ExperienceReview = {
  id: number;
  decision: "APPROVED" | "CHANGES_REQUIRED";
  rationale: string;
  reviewed_at: string;
  reviewer: string;
};

export type SegmentGate = {
  open_segments: number;
  active_segments: number;
  effective_segments: number;
  pending_hour_entries: number;
  segments_missing_final_evaluation: number[];
  combined_review_required: boolean;
  combined_review_approved: boolean;
};

export type SegmentInput = {
  host_org_id: number;
  unit: string;
  workplace_supervisor_id: number;
  start_date: string;
  end_date: string;
  modality: SegmentModality;
  responsibilities: string;
  expected_hours: number | null;
};

export type PlacementHistoryEvent = {
  occurred_at: string;
  action: string;
};

export type DossierChecklistItem = ChecklistItem & {
  versions: DocumentSubmission[];
};

export type CompletionRequirement = {
  kind: string;
  mandatory: boolean;
  satisfied: boolean;
  threshold: number | string | null;
};

export type ProgressReportRecord = {
  revision: number;
  placement_version_id?: number | null;
  version_no?: number | null;
  content: string;
  created_at: string;
  author: string;
  segment_id?: number | null;
  segment_sequence_no?: number | null;
};

export type WorkPlanItem = {
  revision: number;
  placement_version_id?: number | null;
  version_no?: number | null;
  title: string;
  description: string;
  assigned_at: string;
  assigned_by: string;
  segment_id?: number | null;
  segment_sequence_no?: number | null;
};

export type PlacementEvaluationRecord = {
  kind: "MIDTERM" | "FINAL";
  revision: number;
  placement_version_id?: number | null;
  version_no?: number | null;
  narrative: string;
  submitted_at: string;
  evaluator: string;
  segment_id?: number | null;
  segment_sequence_no?: number | null;
};

export type PlacementIncidentRecord = {
  kind: "INCIDENT" | "CHANGE";
  revision: number;
  placement_version_id?: number | null;
  version_no?: number | null;
  status: "REPORTED";
  summary: string;
  description: string;
  reported_at: string;
  reporter: string;
  segment_id?: number | null;
  segment_sequence_no?: number | null;
};

export type CompletionEvidenceRecord = {
  kind: "FINAL_REPORT";
  revision: number;
  placement_version_id?: number | null;
  version_no?: number | null;
  original_filename: string;
  content_type: string;
  byte_size: number;
  sha256: string;
  submitted_at: string;
  submitted_by: string;
};

export type VisiblePlacement = {
  id: number;
  state: string;
  application_state: string;
  opportunity_title: string;
  opportunity_state: string;
  host_org_name: string;
  program_code: string;
  start_date: string | null;
  end_date: string | null;
};

export type PlacementDossier = {
  placement: {
    id: number;
    state: string;
    activation_requirements_instantiated: boolean;
    activation_ready: boolean;
    activation_unmet: string[];
  };
  application: { id: number; state: string; eligibility_result: string | null; eligibility_policy_version: number | null };
  opportunity: {
    id: number;
    title: string;
    state: string;
    host_org_name: string;
    program_code: string;
    program_name: string;
  };
  student: { display_name: string; program_code: string | null; program_name?: string | null };
  current_version: null | {
    version_no: number;
    start_date: string;
    end_date: string;
    location: string;
    responsibilities: string;
    status: string;
    workplace_supervisor_name: string | null;
  };
  versions: {
    id: number;
    version_no: number;
    start_date: string;
    end_date: string;
    location: string;
    responsibilities: string;
    status: string;
    workplace_supervisor_name: string | null;
  }[];
  responsibles: {
    program_coordinators: string[];
    faculty_supervisors: string[];
    faculty_assignments: { id: number; display_name: string }[];
    faculty_assignment_history: {
      action: "ASSIGNED" | "UNASSIGNED";
      occurred_at: string;
      actor_name: string;
      faculty_name: string;
    }[];
  };
  activation_requirements: DossierChecklistItem[];
  completion_requirements: CompletionRequirement[] | null;
  completion_requirements_configured: boolean;
  completion_policy_version: number | null;
  activation_policy_version: number | null;
  documents: DossierChecklistItem[] | null;
  hours: ProgressHoursEntry[] | null;
  hours_total: number | string | null;
  // CR-05 projections (optional so older payloads still render).
  hours_summary?: HoursSummary | null;
  segments?: PlacementSegment[];
  transfers?: PlacementTransfer[];
  experience_reviews?: ExperienceReview[];
  segment_gate?: SegmentGate | null;
  progress_reports: ProgressReportRecord[] | null;
  work_plan: WorkPlanItem[] | null;
  evaluations: PlacementEvaluationRecord[] | null;
  incidents: PlacementIncidentRecord[] | null;
  completion_evidence: CompletionEvidenceRecord[] | null;
  capabilities: {
    read_documents: boolean;
    submit_documents: boolean;
    read_hours: boolean;
    review_documents: boolean;
    decide_academically: boolean;
    record_hours: boolean;
    activate: boolean;
    confirm_completion: boolean;
    close_placement: boolean;
    read_progress_reports: boolean;
    submit_progress_report: boolean;
    read_work_plan: boolean;
    assign_work_plan_item: boolean;
    read_evaluations: boolean;
    submit_evaluation: boolean;
    read_incidents: boolean;
    report_incident: boolean;
    read_completion_evidence: boolean;
    submit_completion_evidence: boolean;
    read_joint_messages: boolean;
    read_academic_messages: boolean;
    manage_faculty_assignments: boolean;
    may_configure_faculty_assignments: boolean;
    faculty_assignment_authority_configured: boolean;
    read_faculty_assignment_history: boolean;
    propose_change: boolean;
    approve_change: boolean;
    manage_segments?: boolean;
    confirm_segment_conditions?: boolean;
    review_hours?: boolean;
    review_combined_experience?: boolean;
    read_segment_internal?: boolean;
  };
  activity: PlacementHistoryEvent[];
};

export type UserNotification = {
  id: number;
  category: "APPLICATION_SUBMITTED" | "APPLICATION_SELECTED" | "DOCUMENT_ACTIVITY"
    | "ELIGIBILITY_REVIEW"
    | "PLACEMENT_ACTIVATED" | "PROGRESS_REPORTED" | "EVALUATION_SUBMITTED"
    | "INCIDENT_REPORTED" | "CHANGE_REPORTED" | "PLACEMENT_COMPLETED"
    | "PLACEMENT_CLOSED" | "MESSAGE_RECEIVED" | "OPPORTUNITY_REVIEW"
    | "OPPORTUNITY_PUBLISHED" | "OPPORTUNITY_CLOSED" | "SEGMENT_CHANGED";
  placement_id: number | null;
  opportunity_id: number | null;
  created_at: string;
  read_at: string | null;
  is_read: boolean;
};

export type PlacementMessage = {
  id: number;
  audience: "JOINT" | "ACADEMIC";
  author_name: string;
  content: string;
  created_at: string;
};

export type OperationalReport = {
  placements_by_state: { state: string; count: number }[];
  opportunities_by_state: { state: string; count: number }[];
  applications_by_state: { state: string; count: number }[];
  active_placements: number;
  mandatory_documents_pending: number;
  reported_incidents: number;
  expected_end_dates: { end_date: string; placements: number }[];
  by_program: { program_id: number; program_code: string; program_name: string; opportunities: number; applications: number; placements: number }[];
  by_organization: { organization_id: number; organization: string; opportunities: number; applications: number; placements: number }[];
};

/** CR-05 aggregates returned by `GET /reports/rotations` (no names, reasons or entries). */
export type RotationReport = {
  multi_segment_placements: number;
  single_segment_placements: number;
  active_rotations: number;
  segments_by_status: { status: SegmentStatus; count: number }[];
  transfers: number;
  transfers_by_treatment: { treatment: WorkRecognition; count: number }[];
  interruptions: number;
  interruptions_by_recognition: { recognition: WorkRecognition; count: number }[];
  hours: { reported: number; accepted: number; not_recognized: number; pending_entries: number; disputed_entries: number };
  active_segments_without_final_evaluation: number;
  completed_segments_missing_final_evaluation: number;
  pending_consolidations: number;
  by_program: { program_id: number; program_code: string; program_name: string; multi_segment_placements: number;
    pending_consolidations: number; transfers: number; interruptions: number }[];
};

// Clear the previous demo JWT if a browser still has it. Current sessions use an HttpOnly cookie.
if (typeof window !== "undefined") localStorage.removeItem("dh05_token");

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  let resp: Response;
  try {
    resp = await fetch(path, { ...options, headers, credentials: "same-origin" });
  } catch {
    throw new Error("No fue posible conectar con el servicio. Inténtalo de nuevo.");
  }
  if (!resp.ok) {
    let detail: unknown = null;
    try {
      const body = await resp.json();
      detail = body?.error ?? body?.detail;
    } catch {
      /* ignore */
    }
    throw new Error(presentApiError(detail, resp.status));
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

function presentApiError(error: unknown, status: number): string {
  const code = typeof error === "string" ? error.toUpperCase() : "";
  const messages: Record<string, string> = {
    UNAUTHORIZED: "Tu sesión terminó. Inicia sesión nuevamente.",
    NOT_FOUND: "No se encontró la información solicitada.",
    FORBIDDEN: "No tienes permiso para realizar esta acción.",
    TOO_MANY_REQUESTS: "Espera un momento antes de volver a intentarlo.",
    INVALID_TRANSITION: "Esta acción no se puede realizar en el estado actual.",
    OPPORTUNITY_INVALID_TRANSITION: "La oportunidad no puede avanzar desde su estado actual.",
    OPPORTUNITY_REVIEW_AUTHORITY_UNCONFIGURED: "La autoridad institucional de revisión aún no está configurada.",
    OPPORTUNITY_PUBLISH_AUTHORITY_UNCONFIGURED: "La autoridad institucional de publicación aún no está configurada.",
    CHANGE_EMPTY: "Indica al menos un campo para proponer un cambio.",
    VERSION_NOT_FOUND: "La versión propuesta no pertenece a esta práctica.",
    CURRENT_VERSION_MISSING: "La práctica no tiene una versión vigente válida.",
    STALE_VERSION: "La versión propuesta quedó desactualizada frente a un cambio más reciente.",
    FACULTY_ASSIGNMENT_AUTHORITY_UNCONFIGURED: "La autoridad institucional para asignar supervisión docente aún no está configurada.",
    FACULTY_ASSIGNMENT_PLACEMENT_TERMINAL: "La práctica ya completó su ciclo y no admite cambios de supervisión docente.",
    FACULTY_SUPERVISOR_INVALID: "Selecciona una cuenta activa con rol de supervisión docente.",
    FACULTY_ALREADY_ASSIGNED: "Esa persona ya está asignada a la práctica.",
    FACULTY_ASSIGNMENT_NOT_FOUND: "No existe una asignación docente activa con esos datos.",
    OPPORTUNITY_NOT_PUBLISHED: "La oportunidad ya no está disponible para postulaciones.",
    NO_POLICY_IN_EFFECT: "No hay una política de elegibilidad vigente para el programa.",
    UNKNOWN_PROGRAM: "No se encontró el programa indicado.",
    POLICY_INVALID: "La configuración de la política no es válida.",
    APPLICATION_NOT_ELIGIBLE: "La postulación no cumple los criterios de elegibilidad.",
    INVALID_PLACEMENT_DATES: "La fecha de inicio debe ser anterior o igual a la fecha de finalización.",
    SUPERVISOR_NOT_ASSIGNED_TO_HOST_ORG: "El supervisor laboral debe pertenecer a la organización anfitriona.",
    INVALID_HOURS: "Ingresa una cantidad de horas finita y mayor que cero.",
    COMPLETION_EVIDENCE_MISSING: "Falta completar evidencia obligatoria de la práctica.",
    COMPLETION_POLICY_MISSING: "No hay una política de finalización configurada para el programa.",
    ACTIVATION_CONDITIONS_UNMET: "Faltan requisitos obligatorios para activar la práctica.",
    ACTIVATION_POLICY_MISSING: "No hay una política de activación configurada para el programa.",
    ACTIVATION_NONCOMPLIANT: "La práctica tiene requisitos obligatorios pendientes.",
    PLACEMENT_NOT_ACTIVE: "Esta acción está disponible cuando la práctica está activa.",
    PLACEMENT_CLOSED: "La práctica está cerrada y ya no admite nuevas actividades del plan.",
    GATE_VIOLATION: "La práctica no cumple las condiciones necesarias para este cambio.",
    DOCUMENT_FILENAME_INVALID: "El nombre del archivo no es válido.",
    DOCUMENT_EMPTY: "El archivo está vacío.",
    DOCUMENT_TOO_LARGE: "El archivo supera el tamaño máximo permitido.",
    DOCUMENT_TYPE_UNSUPPORTED: "El formato del archivo no está permitido.",
    DOCUMENT_NOT_UPLOADABLE: "Este requisito no admite la entrega de archivos.",
    DOCUMENT_DECISION_INVALID: "La decisión documental no es válida.",
    DOCUMENT_REVIEW_REASON_REQUIRED: "Escribe el motivo de la decisión documental.",
    DOCUMENT_NOT_REVIEWABLE: "Este documento no puede revisarse en su estado actual.",
    DOCUMENT_SUBMISSION_MISSING: "No se encontró una entrega para revisar.",
    INVALID_ROLE: "El rol seleccionado no es válido.",
    INVALID_USERNAME: "El nombre de usuario no cumple el formato requerido.",
    USERNAME_UNAVAILABLE: "Ese nombre de usuario ya está en uso.",
    INVITATION_USED: "La invitación ya fue utilizada.",
    INVITATION_EXPIRED: "La invitación venció.",
    INVITATION_ACCOUNT_EXISTS: "Ya existe una cuenta para esta invitación.",
    PASSWORD_RESET_INVALID: "El enlace de restablecimiento no es válido o ya venció.",
    AUDIT_MISSING: "No se pudo guardar el cambio. Inténtalo de nuevo.",
    NO_ACTIVE_SEGMENT: "No hay un segmento activo: las horas solo se registran en el segmento vigente.",
    HOURS_WORK_DATE_INVALID: "La fecha debe estar dentro del periodo del segmento activo y no puede ser futura.",
    HOURS_DAILY_LIMIT: "Las horas registradas para ese día superarían 24 h.",
    HOURS_DESCRIPTION_TOO_LONG: "La descripción supera la longitud permitida.",
    HOURS_REVIEW_INVALID: "Las horas aceptadas deben ser mayores que cero y no superar las reportadas.",
    HOURS_REVIEW_OUTSIDE_SEGMENT: "Solo puedes revisar horas del segmento que supervisas actualmente.",
    HOURS_REVIEW_DECISION_INVALID: "La decisión de revisión de horas no es válida.",
    HOURS_REVIEW_REASON_INVALID: "El motivo de revisión no es válido.",
    SEGMENT_FIELD_REQUIRED: "Completa los campos obligatorios del segmento.",
    SEGMENT_FIELD_TOO_LONG: "Uno de los textos supera la longitud permitida.",
    SEGMENT_MODALITY_INVALID: "Selecciona una modalidad válida.",
    SEGMENT_DATES_INVALID: "La fecha de fin del segmento debe ser igual o posterior a la de inicio.",
    SEGMENT_EXPECTED_HOURS_INVALID: "Las horas esperadas deben ser mayores que cero.",
    SEGMENT_ORGANIZATION_INVALID: "La organización indicada no existe.",
    SEGMENT_SUPERVISOR_INVALID: "El supervisor debe pertenecer a la organización del segmento.",
    SEGMENT_NOT_PLANNED: "El segmento ya no está planificado.",
    SEGMENT_NOT_ACTIVE: "El segmento no está activo.",
    SEGMENT_ALREADY_ACTIVE: "Ya existe un segmento activo; ciérralo o transfiérelo antes de activar otro.",
    SEGMENT_CONDITIONS_UNMET: "El segmento tiene condiciones de habilitación pendientes.",
    SEGMENT_CONDITION_ALREADY_SATISFIED: "La condición ya fue confirmada.",
    SEGMENT_FINAL_EVALUATION_MISSING: "Falta la evaluación final de este segmento.",
    SEGMENT_END_DATE_INVALID: "La fecha de cierre debe estar dentro del periodo del segmento y no ser futura.",
    SEGMENT_RECOGNITION_INVALID: "Indica si se reconocen las horas aceptadas del segmento.",
    SEGMENT_REQUIREMENTS_PENDING: "Hay segmentos abiertos, horas sin revisar o falta la revisión de la experiencia combinada.",
    SEGMENTS_STILL_OPEN: "Cierra todos los segmentos antes de revisar la experiencia combinada.",
    TRANSFER_TREATMENT_INVALID: "Indica el tratamiento del trabajo previo.",
    TRANSFER_EFFECTIVE_DATE_INVALID: "La fecha de efecto debe estar dentro del segmento de origen y no ser futura.",
    TRANSFER_DESTINATION_DATES_INVALID: "El destino no puede comenzar antes de la fecha de efecto.",
    EXPERIENCE_REVIEW_DECISION_INVALID: "La decisión de revisión no es válida.",
    EXPERIENCE_REVIEW_RATIONALE_REQUIRED: "Escribe la justificación de la revisión académica.",
    SEGMENT_CONTEXT: "El registro debe pertenecer al segmento activo de la práctica.",
    SEGMENT_GATE: "El segmento no cumple las condiciones necesarias para este cambio.",
  };
  if (messages[code]) return messages[code];
  if (status === 401) return "Tu sesión terminó. Inicia sesión nuevamente.";
  if (status === 403) return "No tienes permiso para realizar esta acción.";
  if (status === 404) return "No se encontró la información solicitada.";
  if (status === 409) return "No se pudo completar la acción en el estado actual.";
  return "No se pudo completar la solicitud. Inténtalo de nuevo.";
}

export function login(identifier: string, password: string): Promise<{ authenticated: true }> {
  return request<{ authenticated: true }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ identifier, password }),
  });
}

export function me(): Promise<User> {
  return request<User>("/auth/me");
}

export function logout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
}

export type PasswordResetRequest = {
  message: string;
  development_token?: string;
  delivery_mode?: string;
};

export function requestPasswordReset(email: string): Promise<PasswordResetRequest> {
  return request<PasswordResetRequest>("/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function completePasswordReset(token: string, password: string): Promise<{ password_updated: true }> {
  return request<{ password_updated: true }>("/auth/password-reset/complete", {
    method: "POST",
    body: JSON.stringify({ token, password }),
  });
}

export function listOpportunities(): Promise<Opportunity[]> {
  return request<Opportunity[]>("/opportunities");
}

export function listOpportunityCatalogs(): Promise<OpportunityCatalogs> {
  return request<OpportunityCatalogs>("/opportunities/catalogs");
}

export function listWorkplaceSupervisors(opportunity_id: number): Promise<WorkplaceSupervisor[]> {
  return request<WorkplaceSupervisor[]>(`/opportunities/${opportunity_id}/workplace-supervisors`);
}

export function createOpportunity(body: {
  host_org_id: number;
  program_id: number;
  title: string;
}): Promise<{ id: number; state: string }> {
  return request<{ id: number; state: string }>("/opportunities", { method: "POST", body: JSON.stringify(body) });
}

export function submitOpportunityForReview(id: number): Promise<void> {
  return request<void>(`/opportunities/${id}/submit-review`, { method: "POST" });
}

export function approveOpportunity(id: number): Promise<void> {
  return request<void>(`/opportunities/${id}/approve`, { method: "POST" });
}

export function publishOpportunity(id: number): Promise<void> {
  return request<void>(`/opportunities/${id}/publish`, { method: "POST" });
}

export function closeOpportunity(id: number): Promise<void> {
  return request<void>(`/opportunities/${id}/close`, { method: "POST" });
}

export function apply(opportunity_id: number): Promise<{
  application_id: number;
  state: string;
  eligibility: unknown;
}> {
  return request<{
    application_id: number;
    state: string;
    eligibility: unknown;
  }>(`/opportunities/${opportunity_id}/apply`, { method: "POST" });
}

export function listApplications(): Promise<Application[]> {
  return request<Application[]>("/applications");
}

export function listPendingEligibilityReviews(): Promise<PendingEligibilityReview[]> {
  return request<PendingEligibilityReview[]>("/applications/pending-eligibility-review");
}

export function reviewEligibility(
  applicationId: number,
  body: { decision: "ELIGIBLE" | "INELIGIBLE"; rationale: string },
): Promise<{ application_id: number; state: string; eligibility: unknown }> {
  return request(`/applications/${applicationId}/eligibility-review`, {
    method: "POST", body: JSON.stringify(body),
  });
}

export function listApplicationsForOpportunity(oid: number): Promise<EmployerApplication[]> {
  return request<EmployerApplication[]>(`/opportunities/${oid}/applications`);
}

export function selectApplication(
  aid: number,
  body: {
    workplace_supervisor_id: number | null;
    start_date: string;
    end_date: string;
    location: string;
    responsibilities: string;
  },
): Promise<{ placement_id: number }> {
  return request<{ placement_id: number }>(`/applications/${aid}/select`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listPendingAcademic(): Promise<PendingAcademic[]> {
  return request<PendingAcademic[]>("/placements/pending-academic");
}

export function listVisiblePlacements(): Promise<VisiblePlacement[]> {
  return request<VisiblePlacement[]>("/placements");
}

export function getPlacementDossier(pid: number): Promise<PlacementDossier> {
  return request<PlacementDossier>(`/placements/${pid}/dossier`);
}

export function proposePlacementChange(pid: number, changes: {
  start_date?: string;
  end_date?: string;
  location?: string;
  responsibilities?: string;
}): Promise<{ version_id: number; status: string }> {
  return request<{ version_id: number; status: string }>(`/placements/${pid}/changes`, {
    method: "POST", body: JSON.stringify(changes),
  });
}

export function approvePlacementChange(pid: number, version_id: number): Promise<void> {
  return request<void>(`/placements/${pid}/changes/approve`, {
    method: "POST", body: JSON.stringify({ version_id }),
  });
}

export function listFacultySupervisorOptions(pid: number): Promise<{ id: number; display_name: string }[]> {
  return request<{ id: number; display_name: string }[]>(`/placements/${pid}/faculty-supervisors`);
}

export function assignFacultySupervisor(pid: number, user_id: number): Promise<void> {
  return request<void>(`/placements/${pid}/faculty-supervisors`, {
    method: "POST", body: JSON.stringify({ user_id }),
  });
}

export function unassignFacultySupervisor(pid: number, user_id: number): Promise<void> {
  return request<void>(`/placements/${pid}/faculty-supervisors/${user_id}`, { method: "DELETE" });
}

export function listNotifications(): Promise<UserNotification[]> {
  return request<UserNotification[]>("/notifications");
}

export function markNotificationRead(id: number): Promise<{ id: number; read_at: string }> {
  return request<{ id: number; read_at: string }>(`/notifications/${id}/read`, { method: "POST" });
}

export function listPlacementMessages(pid: number, audience: "JOINT" | "ACADEMIC"): Promise<PlacementMessage[]> {
  const params = new URLSearchParams({ audience });
  return request<PlacementMessage[]>(`/placements/${pid}/messages?${params.toString()}`);
}

export function sendPlacementMessage(pid: number, audience: "JOINT" | "ACADEMIC", content: string): Promise<PlacementMessage> {
  return request<PlacementMessage>(`/placements/${pid}/messages`, {
    method: "POST", body: JSON.stringify({ audience, content }),
  });
}

export function getRotationReports(filters: { program_id?: number; organization_id?: number } = {}): Promise<RotationReport> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined) params.set(key, String(value));
  }
  const query = params.toString();
  return request<RotationReport>(`/reports/rotations${query ? `?${query}` : ""}`);
}

export function getOperationalReports(filters: {
  program_id?: number;
  organization_id?: number;
  placement_state?: string;
  opportunity_state?: string;
  application_state?: string;
} = {}): Promise<OperationalReport> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const query = params.toString();
  return request<OperationalReport>(`/reports/operations${query ? `?${query}` : ""}`);
}

export function approveAcademic(pid: number): Promise<void> {
  return request<void>(`/placements/${pid}/approve-academic`, { method: "POST" });
}

export function rejectAcademic(pid: number, reason: string): Promise<void> {
  return request<void>(`/placements/${pid}/reject-academic`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export type ChecklistItem = { id: number; kind: string; mandatory: boolean; status: string };

export type DocumentSubmission = {
  id: number;
  revision: number;
  original_filename: string;
  content_type: string;
  byte_size: number;
  sha256: string;
  submitted_at: string;
  submitted_by: string;
  decision: "APPROVED" | "REJECTED" | null;
  reason: string | null;
  reviewed_at: string | null;
  reviewer: string | null;
};

export type ActivationStatus = {
  placement_id: number;
  state: string;
  activation_requirements_instantiated: boolean;
  activation_noncompliant: boolean;
  ready_to_activate: boolean;
  unmet: string[];
  items: ChecklistItem[];
};

export function listChecklist(pid: number): Promise<ChecklistItem[]> {
  return request<ChecklistItem[]>(`/placements/${pid}/checklist`);
}

export function activationStatus(pid: number): Promise<ActivationStatus> {
  return request<ActivationStatus>(`/placements/${pid}/activation-status`);
}

export function submitDocument(pid: number, item_id: number, file: File): Promise<{ id: number; revision: number }> {
  const query = new URLSearchParams({ filename: file.name });
  return request<{ id: number; revision: number }>(
    `/placements/${pid}/items/${item_id}/submit?${query.toString()}`,
    { method: "POST", headers: { "Content-Type": file.type || "application/octet-stream" }, body: file },
  );
}

export function reviewDocument(
  pid: number,
  item_id: number,
  decision: "APPROVED" | "REJECTED",
  reason: string,
): Promise<void> {
  return request<void>(`/placements/${pid}/items/${item_id}/review`, {
    method: "POST",
    body: JSON.stringify({ decision, reason }),
  });
}

export function listDocumentSubmissions(pid: number, item_id: number): Promise<DocumentSubmission[]> {
  return request<DocumentSubmission[]>(`/placements/${pid}/items/${item_id}/submissions`);
}

export async function downloadDocument(pid: number, item_id: number, submission: DocumentSubmission): Promise<void> {
  const response = await fetch(
    `/placements/${pid}/items/${item_id}/submissions/${submission.id}/download`,
    { credentials: "same-origin" },
  );
  if (!response.ok) throw new Error("No fue posible descargar el archivo. Verifica tus permisos o inténtalo de nuevo.");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = submission.original_filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export function listDocumentsPending(): Promise<{ id: number; state: string; display_name: string; program_code: string; opportunity_title: string }[]> {
  return request<{ id: number; state: string; display_name: string; program_code: string; opportunity_title: string }[]>(
    "/placements/documents-pending",
  );
}

export function listPendingActivation(): Promise<{ id: number; state: string; display_name: string; program_code: string; opportunity_title: string }[]> {
  return request<{ id: number; state: string; display_name: string; program_code: string; opportunity_title: string }[]>(
    "/placements/pending-activation",
  );
}

export function activatePlacement(pid: number): Promise<void> {
  return request<void>(`/placements/${pid}/activate`, { method: "POST" });
}

export function confirmPlacementCompletion(pid: number): Promise<void> {
  return request<void>(`/placements/${pid}/confirm-completion`, { method: "POST" });
}

export function closePlacement(pid: number): Promise<void> {
  return request<void>(`/placements/${pid}/close`, { method: "POST" });
}

export function recordPlacementHours(
  pid: number,
  hours: number,
  details: { work_date?: string; description?: string } = {},
): Promise<void> {
  const body: Record<string, unknown> = { hours };
  if (details.work_date) body.work_date = details.work_date;
  if (details.description?.trim()) body.description = details.description.trim();
  return request<void>(`/placements/${pid}/hours`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ------------------------------------------------------------ CR-05 segments

export function listPlacementSegments(pid: number): Promise<PlacementSegment[]> {
  return request<PlacementSegment[]>(`/placements/${pid}/segments`);
}

export function createPlacementSegment(pid: number, segment: SegmentInput): Promise<{ segment_id: number; sequence_no: number; status: "PLANNED" }> {
  return request(`/placements/${pid}/segments`, { method: "POST", body: JSON.stringify(segment) });
}

export function confirmSegmentCondition(pid: number, sid: number, conditionId: number, reference: string): Promise<void> {
  return request<void>(`/placements/${pid}/segments/${sid}/conditions/${conditionId}/confirm`, {
    method: "POST", body: JSON.stringify({ reference }),
  });
}

export function activatePlacementSegment(pid: number, sid: number): Promise<void> {
  return request<void>(`/placements/${pid}/segments/${sid}/activate`, { method: "POST" });
}

export function completePlacementSegment(pid: number, sid: number, ended_on?: string): Promise<void> {
  return request<void>(`/placements/${pid}/segments/${sid}/complete`, {
    method: "POST", body: JSON.stringify(ended_on ? { ended_on } : {}),
  });
}

export function terminatePlacementSegment(pid: number, sid: number, body: {
  ended_on: string;
  reason_shared: string;
  reason_internal?: string;
  work_recognition: WorkRecognition;
  recognition_note?: string;
}): Promise<void> {
  return request<void>(`/placements/${pid}/segments/${sid}/terminate`, { method: "POST", body: JSON.stringify(body) });
}

export function cancelPlacementSegment(pid: number, sid: number, reason_shared: string): Promise<void> {
  return request<void>(`/placements/${pid}/segments/${sid}/cancel`, {
    method: "POST", body: JSON.stringify({ reason_shared }),
  });
}

export function reschedulePlacementSegment(pid: number, sid: number, body: {
  start_date?: string;
  end_date: string;
  reason_shared: string;
}): Promise<{ segment_id: number; start_date: string; end_date: string; change: "EXTENDED" | "SHORTENED" | "MOVED" }> {
  return request(`/placements/${pid}/segments/${sid}/schedule`, { method: "POST", body: JSON.stringify(body) });
}

export function transferPlacementSegment(pid: number, sid: number, body: {
  effective_date: string;
  reason_shared: string;
  reason_internal?: string;
  prior_work_treatment: WorkRecognition;
  destination: SegmentInput;
}): Promise<{ transfer_id: number; to_segment_id: number; to_sequence_no: number; status: "PLANNED" }> {
  return request(`/placements/${pid}/segments/${sid}/transfer`, { method: "POST", body: JSON.stringify(body) });
}

export type SegmentOption = { id: number; name: string; supervisors: { id: number; display_name: string }[] };

export function listSegmentOptions(pid: number): Promise<SegmentOption[]> {
  return request<SegmentOption[]>(`/placements/${pid}/segment-options`);
}

export function listPlacementTransfers(pid: number): Promise<PlacementTransfer[]> {
  return request<PlacementTransfer[]>(`/placements/${pid}/transfers`);
}

export function getHoursSummary(pid: number): Promise<HoursSummary> {
  return request<HoursSummary>(`/placements/${pid}/hours/summary`);
}

export function reviewPlacementHours(pid: number, entryId: number, body: {
  decision: "ACCEPTED" | "REJECTED" | "DISPUTED";
  accepted_hours?: number;
  reason_code?: HoursReviewReason;
  reason?: string;
}): Promise<{ review_id: number; decision: string; accepted_hours: number | string | null; reviewed_at: string }> {
  return request(`/placements/${pid}/hours/${entryId}/review`, { method: "POST", body: JSON.stringify(body) });
}

export function recordExperienceReview(pid: number, decision: "APPROVED" | "CHANGES_REQUIRED", rationale: string): Promise<{ review_id: number; decision: string; reviewed_at: string }> {
  return request(`/placements/${pid}/experience-review`, {
    method: "POST", body: JSON.stringify({ decision, rationale }),
  });
}

export function listPlacementHours(pid: number): Promise<ProgressHoursEntry[]> {
  return request<ProgressHoursEntry[]>(`/placements/${pid}/hours`);
}

export function submitProgressReport(pid: number, content: string): Promise<{ revision: number; created_at: string }> {
  return request<{ revision: number; created_at: string }>(`/placements/${pid}/progress-reports`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function listWorkPlan(pid: number): Promise<WorkPlanItem[]> {
  return request<WorkPlanItem[]>(`/placements/${pid}/work-plan`);
}

export function assignWorkPlanItem(
  pid: number,
  title: string,
  description: string,
): Promise<{ revision: number; assigned_at: string }> {
  return request<{ revision: number; assigned_at: string }>(`/placements/${pid}/work-plan`, {
    method: "POST",
    body: JSON.stringify({ title, description }),
  });
}

export function submitPlacementEvaluation(
  pid: number,
  kind: "MIDTERM" | "FINAL",
  narrative: string,
): Promise<{ kind: "MIDTERM" | "FINAL"; revision: number; submitted_at: string }> {
  return request<{ kind: "MIDTERM" | "FINAL"; revision: number; submitted_at: string }>(`/placements/${pid}/evaluations`, {
    method: "POST",
    body: JSON.stringify({ kind, narrative }),
  });
}

export function reportPlacementIncident(
  pid: number,
  kind: "INCIDENT" | "CHANGE",
  summary: string,
  description: string,
): Promise<{ kind: "INCIDENT" | "CHANGE"; revision: number; reported_at: string }> {
  return request<{ kind: "INCIDENT" | "CHANGE"; revision: number; reported_at: string }>(`/placements/${pid}/incidents`, {
    method: "POST",
    body: JSON.stringify({ kind, summary, description }),
  });
}

export function submitCompletionEvidence(pid: number, file: File): Promise<{ kind: "FINAL_REPORT"; revision: number; submitted_at: string }> {
  const query = new URLSearchParams({ filename: file.name });
  return request<{ kind: "FINAL_REPORT"; revision: number; submitted_at: string }>(`/placements/${pid}/completion-evidence/FINAL_REPORT?${query.toString()}`, {
    method: "POST",
    headers: { "Content-Type": file.type || "application/octet-stream" },
    body: file,
  });
}

export async function downloadCompletionEvidence(pid: number, evidence: CompletionEvidenceRecord): Promise<void> {
  const response = await fetch(
    `/placements/${pid}/completion-evidence/${evidence.kind}/${evidence.revision}/download`,
    { credentials: "same-origin" },
  );
  if (!response.ok) throw new Error("No fue posible descargar la evidencia final. Verifica tus permisos o inténtalo de nuevo.");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = evidence.original_filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export async function listPlacementHistory(pid: number): Promise<PlacementHistoryEvent[]> {
  const payload = await request<unknown>(`/placements/${pid}/history`);
  if (!Array.isArray(payload)) return [];
  return payload.flatMap((event): PlacementHistoryEvent[] => {
    if (event === null || typeof event !== "object" || Array.isArray(event)) return [];
    const record = event as Record<string, unknown>;
    return [{
      occurred_at: typeof record.occurred_at === "string" ? record.occurred_at : "",
      action: typeof record.action === "string" ? record.action : "",
    }];
  });
}

export type PolicyKind = "ELIGIBILITY" | "ACTIVATION" | "COMPLETION";
export type PolicyCondition = { type: string; value: string[] | number | boolean };
export type PolicyVersion = {
  id: number;
  version_no: number;
  conditions: PolicyCondition[];
  created_reason?: string | null;
  created_by_name?: string | null;
};
export type ProgramPolicies = {
  id: number;
  code: string;
  name: string;
  policies: Partial<Record<PolicyKind, PolicyVersion>>;
};

export function listPolicies(): Promise<ProgramPolicies[]> {
  return request<ProgramPolicies[]>("/policies");
}

export function createPolicyVersion(
  program_code: string,
  kind: PolicyKind,
  conditions: PolicyCondition[],
  reason: string,
): Promise<{ id: number }> {
  return request<{ id: number }>("/policies", {
    method: "POST",
    body: JSON.stringify({ program_code, kind, conditions, reason }),
  });
}
