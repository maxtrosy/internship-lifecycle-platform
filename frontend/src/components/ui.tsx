import type { ReactNode } from "react";

const DOMAIN_LABELS: Record<string, string> = {
  ACTIVE: "Activa",
  APPROVED: "Aprobado",
  CANCELLED: "Cancelada",
  CLOSED: "Cerrada",
  COMPLETED: "Completada",
  DOCUMENTATION_PENDING: "Documentación pendiente",
  DRAFT: "Borrador",
  ELIGIBLE: "Elegible",
  INELIGIBLE: "No elegible",
  NOT_ELIGIBLE: "No elegible",
  PENDING_ELIGIBILITY_REVIEW: "Revisión académica pendiente",
  REQUIRES_REVIEW: "Requiere revisión académica",
  "Elegible": "Elegible",
  "No elegible": "No elegible",
  "Estado no disponible": "Estado no disponible",
  PENDING_ACADEMIC_APPROVAL: "Pendiente de aprobación académica",
  IN_REVIEW: "En revisión",
  PUBLISHED: "Publicada",
  REJECTED: "Rechazado",
  REPORTED: "Reportado",
  REQUIRED: "Pendiente",
  SELECTED: "Seleccionada",
  SUBMITTED: "Enviada",
  PROPOSED: "Propuesta",
  ELIGIBILITY: "Elegibilidad",
  ACTIVATION: "Activación",
  COMPLETION: "Finalización",
  PROGRAM_IN: "Programas permitidos",
  ACADEMIC_LEVEL_MIN: "Nivel académico mínimo",
  CREDITS_MIN: "Créditos mínimos",
  PREREQUISITE_COMPLETED: "Prerrequisitos aprobados",
  MANUAL_REVIEW: "Revisión manual de elegibilidad",
  REQUIRE_DOCUMENTS: "Documentos obligatorios",
  DOC_AGREEMENT: "Convenio",
  DOC_INSURANCE: "Seguro",
  COND_SUPERVISOR_ASSIGNED: "Supervisor asignado",
  FINAL_REPORT: "Informe final",
  FINAL_EVALUATION: "Evaluación final",
  MIDTERM: "Evaluación intermedia",
  FINAL: "Evaluación final",
  INCIDENT: "Situación o problema",
  CHANGE: "Cambio reportado",
  MIN_HOURS: "Horas mínimas",
  SUPERVISORS_ASSIGNED: "Supervisores asignados",
  STUDENT: "Estudiante",
  HOST_ORG_MEMBER: "Representante de organización",
  WORKPLACE_SUPERVISOR: "Supervisor de empresa",
  FACULTY_SUPERVISOR: "Supervisor académico",
  PROGRAM_COORDINATOR: "Coordinador de programa",
  EXPERIENTIAL_COORDINATOR: "Coordinador de prácticas",
  LEGAL_REVIEWER: "Revisor jurídico",
};

export function formatDomainLabel(value: string): string {
  if (DOMAIN_LABELS[value]) return DOMAIN_LABELS[value];
  const [kind, status, ...rest] = value.split("=");
  if (status !== undefined) return `${formatDomainLabel(kind)}: ${formatDomainLabel([status, ...rest].join("="))}`;
  return value.replace(/_/g, " ").toLocaleLowerCase("es");
}

export type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

const TONE_BY_STATE: Record<string, StatusTone> = {
  ACTIVE: "success", APPROVED: "success", ELIGIBLE: "success", SATISFIED: "success",
  ACCEPTED: "success", PUBLISHED: "success", SELECTED: "success", COMPLETED: "success", "Elegible": "success",
  PENDING_ACADEMIC_APPROVAL: "warning", PENDING_ELIGIBILITY_REVIEW: "warning", REQUIRES_REVIEW: "warning",
  DOCUMENTATION_PENDING: "warning", REQUIRED: "warning", IN_REVIEW: "warning", SUBMITTED: "warning",
  DISPUTED: "warning", CHANGES_REQUIRED: "warning", PENDING: "warning",
  REJECTED: "danger", CANCELLED: "danger", INELIGIBLE: "danger", NOT_ELIGIBLE: "danger",
  TERMINATED_EARLY: "danger", "No elegible": "danger",
  PLANNED: "info", TRANSFERRED: "info", PROPOSED: "info", REPORTED: "info",
  DRAFT: "neutral", CLOSED: "neutral",
};

/** Presentation tone for a domain state. Unknown values stay neutral. */
export function statusTone(state: string | null | undefined): StatusTone {
  if (!state) return "neutral";
  return TONE_BY_STATE[state] ?? "neutral";
}

export type IconName =
  | "home" | "briefcase" | "clipboard" | "document" | "academic" | "settings" | "review" | "check" | "logout"
  | "arrow" | "bell" | "menu" | "close" | "chevron-left" | "chevron-right" | "chevron-down" | "search"
  | "calendar" | "clock" | "user" | "users" | "building" | "chart" | "inbox" | "contrast"
  | "status-success" | "status-warning" | "status-danger" | "status-info" | "status-neutral" | "segment" | "message";

const ICON_PATHS: Record<IconName, ReactNode> = {
  home: <><path d="m3.5 10 8.5-7 8.5 7" /><path d="M5.5 9v11h13V9M9 20v-6h6v6" /></>,
  briefcase: <><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2" /></>,
  clipboard: <><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4.5h6a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1ZM8 10h8M8 14h8M8 18h5" /></>,
  document: <><path d="M6 3h8l5 5v13H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" /><path d="M14 3v5h5M8 13h8M8 17h8" /></>,
  academic: <><path d="m2.5 9 9.5-5 9.5 5-9.5 5-9.5-5Z" /><path d="M6 11v5c3.6 2.8 8.4 2.8 12 0v-5M21.5 9v6" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.8 1l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.8-1l-1.7.7-1.4-2.4 1.4-1.1a8 8 0 0 1 0-2l-1.4-1.1 1.4-2.4 1.7.7a8 8 0 0 1 1.8-1l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.8 1l1.7-.7 1.4 2.4-1.4 1.1a8 8 0 0 1 0 2Z" /></>,
  review: <><path d="M4 5h16v14H4z" /><path d="m8 12 2.5 2.5L16 9M7 2.5v5M17 2.5v5" /></>,
  check: <><path d="m5 12 4 4L19 6" /></>,
  logout: <><path d="M10 17l5-5-5-5M15 12H3" /><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6" /></>,
  arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
  menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
  close: <><path d="M6 6l12 12M18 6 6 18" /></>,
  "chevron-left": <><path d="m15 6-6 6 6 6" /></>,
  "chevron-right": <><path d="m9 6 6 6-6 6" /></>,
  "chevron-down": <><path d="m6 9 6 6 6-6" /></>,
  search: <><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
  calendar: <><rect x="3.5" y="5" width="17" height="15.5" rx="2" /><path d="M3.5 10h17M8 3v4M16 3v4" /></>,
  clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4.5 20.5c1.2-3.8 4-5.5 7.5-5.5s6.3 1.7 7.5 5.5" /></>,
  users: <><circle cx="9" cy="8.5" r="3.5" /><path d="M2.5 19.5c.9-3.2 3.3-4.8 6.5-4.8s5.6 1.6 6.5 4.8M16 5.3a3.5 3.5 0 0 1 0 6.4M18 14.9c1.8.6 3 2.1 3.5 4.6" /></>,
  building: <><path d="M4 20.5V4.5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v16M15 9h4a1 1 0 0 1 1 1v10.5M2.5 20.5h19" /><path d="M8 7.5h3M8 11.5h3M8 15.5h3" /></>,
  chart: <><path d="M4 20V4M4 20h16" /><path d="M8 16v-5M12 16V8M16 16v-3" /></>,
  inbox: <><path d="M3.5 13.5 6 5h12l2.5 8.5V19a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1v-5.5Z" /><path d="M3.5 13.5H8l1.5 2.5h5l1.5-2.5h4.5" /></>,
  contrast: <><circle cx="12" cy="12" r="8.5" /><path d="M12 3.5v17a8.5 8.5 0 0 0 0-17Z" fill="currentColor" stroke="none" /></>,
  "status-success": <><circle cx="12" cy="12" r="9" /><path d="m8 12.2 2.7 2.7L16.2 9.4" /></>,
  "status-warning": <><circle cx="12" cy="12" r="9" /><path d="M12 7v5.5M12 16.2v.3" /></>,
  "status-danger": <><circle cx="12" cy="12" r="9" /><path d="m9 9 6 6M15 9l-6 6" /></>,
  "status-info": <><circle cx="12" cy="12" r="9" /><path d="M12 11v5.5M12 7.8v.3" /></>,
  "status-neutral": <><circle cx="12" cy="12" r="9" /><path d="M8.5 12h7" /></>,
  segment: <><rect x="3" y="5" width="7" height="14" rx="1.5" /><rect x="14" y="5" width="7" height="14" rx="1.5" /><path d="M10 12h4" /></>,
  message: <><path d="M4 5h16v11H9l-5 4V5Z" /><path d="M8 9.5h8M8 12.5h5" /></>,
};

export function Icon({ name, className = "" }: { name: IconName; className?: string }) {
  return <svg className={`icon ${className}`.trim()} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{ICON_PATHS[name]}</svg>;
}

const TONE_ICON: Record<StatusTone, IconName> = {
  success: "status-success",
  warning: "status-warning",
  danger: "status-danger",
  info: "status-info",
  neutral: "status-neutral",
};

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  showTitle = true,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  showTitle?: boolean;
}) {
  return (
    <div className="page-header">
      <div className="page-header-copy">
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        {showTitle && <h1>{title}</h1>}
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </div>
  );
}

export function BentoCard({
  children,
  title,
  description,
  variant = "content",
  className = "",
}: {
  children: ReactNode;
  title?: string;
  description?: string;
  variant?: "hero" | "metric" | "activity" | "task" | "content" | "action";
  className?: string;
}) {
  return (
    <section className={`bento-card bento-${variant} ${className}`.trim()}>
      {(title || description) && (
        <div className="bento-heading">
          <div>
            {title && <h2>{title}</h2>}
            {description && <p>{description}</p>}
          </div>
        </div>
      )}
      {children}
    </section>
  );
}

export function MetricCard({ label, value, detail }: { label: string; value: number | string | null; detail?: string }) {
  return (
    <BentoCard variant="metric" className="metric-card">
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value ?? <span className="metric-loading">—</span>}</strong>
      {detail && <span className="metric-detail">{detail}</span>}
    </BentoCard>
  );
}

/**
 * Status badge: tone + icon + text, so state is never conveyed by color alone
 * (WCAG 1.4.1). Same props as before; `state` drives the tone.
 */
export function Badge({ children, state, label }: { children: ReactNode; state?: string; label?: ReactNode }) {
  const rawState = state ?? String(children);
  const tone = statusTone(rawState);
  const displayLabel = label ?? (typeof children === "string" ? formatDomainLabel(children) : children);
  return (
    <span className={`badge badge--${tone}`}>
      <Icon name={TONE_ICON[tone]} className="badge-icon" />
      <span>{displayLabel}</span>
    </span>
  );
}

export function Spinner() {
  return <span className="spinner" role="status" aria-label="Cargando" />;
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton-group" aria-hidden="true">
      {Array.from({ length: lines }, (_, index) => (
        <span key={index} className={`skeleton skeleton--w${index % 3}`} />
      ))}
    </div>
  );
}

export function EmptyState({ message, action, icon = "inbox" }: { message: string; action?: ReactNode; icon?: IconName }) {
  return (
    <div className="empty-state">
      <span className="empty-state-icon" aria-hidden="true"><Icon name={icon} /></span>
      <p>{message}</p>
      {action && <div className="empty-action">{action}</div>}
    </div>
  );
}

const ALERT_ICON: Record<"error" | "success" | "info", IconName> = {
  error: "status-danger",
  success: "status-success",
  info: "status-info",
};

export function Alert({ kind, children }: { kind: "error" | "success" | "info"; children: ReactNode }) {
  return (
    <div className={`alert ${kind}`} role={kind === "error" ? "alert" : "status"}>
      <Icon name={ALERT_ICON[kind]} className="alert-icon" />
      <div className="alert-body">{children}</div>
    </div>
  );
}
