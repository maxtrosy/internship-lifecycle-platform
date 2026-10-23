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
    case "SUBMITTED":
    case "DOCUMENTATION_PENDING":
    case "PUBLISHED":
      return "blue";
    case "SELECTED":
    case "PENDING_ACADEMIC_APPROVAL":
      return "amber";
    case "REJECTED":
    case "CANCELLED":
    case "INELIGIBLE":
    case "NOT_ELIGIBLE":
      return "red";
    default:
      return "gray";
  }
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div className="page-header-copy">
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
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
  icon,
  variant = "content",
  className = "",
}: {
  children: ReactNode;
  title?: string;
  description?: string;
  icon?: string;
  variant?: "hero" | "metric" | "activity" | "task" | "content" | "action";
  className?: string;
}) {
  return (
    <section className={`bento-card bento-${variant} ${className}`.trim()}>
      {(title || description || icon) && (
        <div className="bento-heading">
          {icon && <span className="bento-icon" aria-hidden="true">{icon}</span>}
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

export function MetricCard({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: number | string | null;
  detail?: string;
  icon?: string;
}) {
  return (
    <BentoCard variant="metric" className="metric-card">
      <div className="metric-card-top">
        <span className="metric-label">{label}</span>
        {icon && <span className="bento-icon" aria-hidden="true">{icon}</span>}
      </div>
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
      <span className="empty-mark" aria-hidden="true">—</span>
      <p>{message}</p>
      {action && <div className="empty-action">{action}</div>}
    </div>
  );
}

export function Alert({ kind, children }: { kind: "error" | "success" | "info"; children: ReactNode }) {
  return <div className={`alert ${kind}`} role={kind === "error" ? "alert" : "status"}>{children}</div>;
}
