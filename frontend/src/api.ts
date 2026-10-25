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
};

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

export function createOpportunity(body: {
  host_org_id: number;
  program_id: number;
  title: string;
}): Promise<{ id: number }> {
  return request<{ id: number }>("/opportunities", { method: "POST", body: JSON.stringify(body) });
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

export function recordPlacementHours(pid: number, hours: number): Promise<void> {
  return request<void>(`/placements/${pid}/hours`, {
    method: "POST",
    body: JSON.stringify({ hours }),
  });
}

export function listPlacementHours(pid: number): Promise<ProgressHoursEntry[]> {
  return request<ProgressHoursEntry[]>(`/placements/${pid}/hours`);
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
