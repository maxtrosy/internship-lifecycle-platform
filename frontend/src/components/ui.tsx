import type { ReactNode } from "react";

const DOMAIN_LABELS: Record<string, string> = {
  ACTIVE: "Activa",
  APPROVED: "Aprobado",
  CANCELLED: "Cancelada",
  CLOSED: "Cerrada",
  COMPLETED: "Completada",
  DOCUMENTATION_PENDING: "Documentación pendiente",
  ELIGIBLE: "Elegible",
  INELIGIBLE: "No elegible",
  NOT_ELIGIBLE: "No elegible",
  "Elegible": "Elegible",
  "No elegible": "No elegible",
  "Estado no disponible": "Estado no disponible",
  PENDING_ACADEMIC_APPROVAL: "Pendiente de aprobación académica",
  PUBLISHED: "Publicada",
  REJECTED: "Rechazado",
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
  REQUIRE_DOCUMENTS: "Documentos obligatorios",
  DOC_AGREEMENT: "Convenio",
  DOC_INSURANCE: "Seguro",
  COND_SUPERVISOR_ASSIGNED: "Supervisor asignado",
  FINAL_REPORT: "Informe final",
  FINAL_EVALUATION: "Evaluación final",
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

export function statusTone(state: string | null | undefined): string {
  switch (state) {
    case "ACTIVE":
    case "COMPLETED":
    case "APPROVED":
    case "ELIGIBLE":
      return "green";
    case "REJECTED":
    case "CANCELLED":
    case "INELIGIBLE":
    case "NOT_ELIGIBLE":
      return "red";
    default:
      return "gray";
  }
}

export type IconName = "home" | "briefcase" | "clipboard" | "document" | "academic" | "settings" | "review" | "check" | "logout" | "arrow";

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
};

export function Icon({ name, className = "" }: { name: IconName; className?: string }) {
  return <svg className={`icon ${className}`.trim()} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{ICON_PATHS[name]}</svg>;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  showTitle = false,
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

export function Badge({ children, state }: { children: ReactNode; state?: string }) {
  const rawState = state ?? String(children);
  const label = typeof children === "string" ? formatDomainLabel(children) : children;
  return <span className={`badge ${statusTone(rawState)}`}>{label}</span>;
}

export function Spinner() {
  return <span className="spinner" role="status" aria-label="Cargando" />;
}

export function EmptyState({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <p>{message}</p>
      {action && <div className="empty-action">{action}</div>}
    </div>
  );
}

export function Alert({ kind, children }: { kind: "error" | "success" | "info"; children: ReactNode }) {
  return <div className={`alert ${kind}`} role={kind === "error" ? "alert" : "status"}>{children}</div>;
}
