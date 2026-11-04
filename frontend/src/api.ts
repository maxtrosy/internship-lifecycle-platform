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
  content: string;
  created_at: string;
  author: string;
};

export type WorkPlanItem = {
  revision: number;
  title: string;
  description: string;
  assigned_at: string;
  assigned_by: string;
};

export type PlacementEvaluationRecord = {
  kind: "MIDTERM" | "FINAL";
  revision: number;
  narrative: string;
  submitted_at: string;
  evaluator: string;
};

export type PlacementIncidentRecord = {
  kind: "INCIDENT" | "CHANGE";
  revision: number;
  status: "REPORTED";
  summary: string;
  description: string;
  reported_at: string;
  reporter: string;
};

export type CompletionEvidenceRecord = {
  kind: "FINAL_REPORT";
  revision: number;
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
  };
  activity: PlacementHistoryEvent[];
};

export type UserNotification = {
  id: number;
  category: "APPLICATION_SUBMITTED" | "APPLICATION_SELECTED" | "DOCUMENT_ACTIVITY"
    | "PLACEMENT_ACTIVATED" | "PROGRESS_REPORTED" | "EVALUATION_SUBMITTED"
    | "INCIDENT_REPORTED" | "CHANGE_REPORTED" | "PLACEMENT_COMPLETED"
    | "PLACEMENT_CLOSED" | "MESSAGE_RECEIVED" | "OPPORTUNITY_REVIEW"
    | "OPPORTUNITY_PUBLISHED" | "OPPORTUNITY_CLOSED";
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

export function recordPlacementHours(pid: number, hours: number): Promise<void> {
  return request<void>(`/placements/${pid}/hours`, {
    method: "POST",
    body: JSON.stringify({ hours }),
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
export type PolicyVersion = { id: number; version_no: number; conditions: PolicyCondition[] };
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
): Promise<{ id: number }> {
  return request<{ id: number }>("/policies", {
    method: "POST",
    body: JSON.stringify({ program_code, kind, conditions }),
  });
}
