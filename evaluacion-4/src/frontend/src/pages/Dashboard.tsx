import { useEffect, useState } from "react";
import * as api from "../api";
import type { ActivationStatus, Application, EmployerApplication, Opportunity, User } from "../api";
import type { VisiblePlacement } from "../api";
import { Alert, Badge, BentoCard, EmptyState, PageHeader, Skeleton, Spinner, formatDomainLabel } from "../components/ui";
import type { SectionId } from "../components/Layout";
import { getStudentJourney } from "../studentJourney";
import { getRelatedPlacementsState } from "../relatedPlacements";

type DashboardData = {
  opportunities: Opportunity[] | null;
  applications: Application[] | null;
  employerApplications: EmployerApplication[] | null;
  academicQueue: Awaited<ReturnType<typeof api.listPendingAcademic>> | null;
  documentQueue: Awaited<ReturnType<typeof api.listDocumentsPending>> | null;
  activationQueue: Awaited<ReturnType<typeof api.listPendingActivation>> | null;
  studentRequirements: ActivationStatus[] | null;
  visiblePlacements: VisiblePlacement[] | null;
};

const emptyData: DashboardData = {
  opportunities: null,
  applications: null,
  employerApplications: null,
  academicQueue: null,
  documentQueue: null,
  activationQueue: null,
  studentRequirements: null,
  visiblePlacements: null,
};

export default function Dashboard({ user, onNavigate }: { user: User; onNavigate: (s: SectionId) => void }) {
  const [data, setData] = useState<DashboardData>(emptyData);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);
  const [reloadAttempt, setReloadAttempt] = useState(0);

  const roles = user.roles.map((role) => role.role);
  const isStudent = roles.includes("STUDENT");
  const isEmployer = roles.includes("HOST_ORG_MEMBER");
  const isAcademic = roles.includes("PROGRAM_COORDINATOR");
  const isLegal = roles.includes("LEGAL_REVIEWER");
  const isEc = roles.includes("EXPERIENTIAL_COORDINATOR");
  const isWorkplaceSupervisor = roles.includes("WORKPLACE_SUPERVISOR");
  const isFacultySupervisor = roles.includes("FACULTY_SUPERVISOR");
  const dashboardVariant = isStudent ? "student" : isEmployer ? "employer" : isAcademic ? "academic" : isLegal ? "legal" : isEc ? "experiential" : isWorkplaceSupervisor ? "workplace" : isFacultySupervisor ? "faculty" : "limited";
  // Accounts can hold several roles (e.g. supervisor + coordinator). Only the
  // primary role — the same precedence used for `dashboardVariant` — gets the
  // hero; every other role section is rendered as a secondary card so the page
  // keeps a single main heading area instead of stacking several heroes.
  const primaryBlock = dashboardVariant === "workplace" || dashboardVariant === "faculty" ? "supervision" : dashboardVariant;
  const roleHero = (block: "student" | "employer" | "academic" | "supervision" | "legal" | "experiential") => (
    block === primaryBlock
      ? { variant: "hero" as const, className: "dashboard-hero" }
      : { variant: "action" as const, className: "dashboard-role-card" }
  );
  const dashboardEyebrow = isStudent ? "Tu práctica" : isEmployer ? "Organización anfitriona" : isAcademic ? "Coordinación académica" : isLegal ? "Revisión documental" : isEc ? "Coordinación experiencial" : isWorkplaceSupervisor ? "Supervisión laboral" : isFacultySupervisor ? "Supervisión docente" : "Espacio de trabajo";
  const dashboardDescription = isStudent
    ? "Consulta el estado de tus postulaciones y las acciones habilitadas para tu práctica."
    : isEmployer
      ? "Gestiona oportunidades y candidaturas visibles para las relaciones de tu organización."
      : isAcademic
        ? "Revisa selecciones, políticas y prácticas del programa asociado a tu cuenta."
        : isLegal
          ? "Atiende los documentos disponibles en la cola autorizada para tu cuenta."
          : isEc
            ? "Consulta activaciones y tareas de operación institucional disponibles para tu rol."
            : isWorkplaceSupervisor
              ? "Sigue las prácticas y actividades vinculadas a tu relación de supervisión laboral."
              : isFacultySupervisor
                ? "Consulta los expedientes vinculados a tu supervisión académica."
                : "Accede a las secciones disponibles para tu cuenta.";

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setErrors([]);
      const next: DashboardData = { ...emptyData };
      const problems: string[] = [];
      const capture = async <T,>(label: string, operation: () => Promise<T>): Promise<T | null> => {
        try {
          return await operation();
        } catch (error) {
          problems.push(`${label}: ${error instanceof Error ? error.message : "No fue posible cargar esta información."}`);
          return null;
        }
      };

      const [opportunities, applications, academicQueue, documentQueue, activationQueue, visiblePlacements] = await Promise.all([
        capture("Oportunidades", () => api.listOpportunities()),
        isStudent ? capture("Postulaciones", () => api.listApplications()) : Promise.resolve(null),
        isAcademic ? capture("Revisión académica", () => api.listPendingAcademic()) : Promise.resolve(null),
        isLegal ? capture("Revisión documental", () => api.listDocumentsPending()) : Promise.resolve(null),
        isEc ? capture("Activaciones", () => api.listPendingActivation()) : Promise.resolve(null),
        isAcademic || isWorkplaceSupervisor || isFacultySupervisor
          ? capture("Expedientes relacionados", () => api.listVisiblePlacements())
          : Promise.resolve(null),
      ]);
      next.opportunities = opportunities;
      next.applications = applications;
      next.academicQueue = academicQueue;
      next.documentQueue = documentQueue;
      next.activationQueue = activationQueue;
      next.visiblePlacements = visiblePlacements;

      if (isEmployer && opportunities) {
        const lists = await Promise.all(opportunities.map((opportunity) =>
          capture(`Postulaciones de ${opportunity.title}`, () => api.listApplicationsForOpportunity(opportunity.id)),
        ));
        next.employerApplications = lists.flatMap((list) => list ?? []);
      }

      if (isStudent && applications) {
        const placements = applications.filter((application) => application.placement_id &&
          (application.placement_state === "DOCUMENTATION_PENDING" || application.placement_state === "ACTIVE"));
        const statuses = await Promise.all(placements.map((application) =>
          capture(`Requisitos de ${application.title}`, () => api.activationStatus(application.placement_id!)),
        ));
        next.studentRequirements = statuses.filter((status): status is ActivationStatus => status !== null);
      }

      if (!cancelled) {
        setData(next);
        setErrors(problems);
        setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [isStudent, isEmployer, isAcademic, isLegal, isEc, isWorkplaceSupervisor, isFacultySupervisor, reloadAttempt]);

  const latestApplication = data.applications?.[0];
  const pendingDecisions = data.employerApplications?.filter((application) => application.state === "SUBMITTED").length ?? null;
  const selectedCandidates = data.employerApplications?.filter((application) => application.placement_id !== null).length ?? null;
  const studentUnmet = data.studentRequirements?.reduce((total, status) => total + status.unmet.length, 0) ?? null;
  const relatedPlacementsFailed = errors.some((error) => error.startsWith("Expedientes relacionados:"));
  const relatedPlacementsState = getRelatedPlacementsState(data.visiblePlacements, loading, relatedPlacementsFailed);

  const studentJourney = getStudentJourney(
    latestApplication,
    latestApplication?.placement_id ? data.studentRequirements?.find((status) => status.placement_id === latestApplication.placement_id) : undefined,
    loading,
    data.applications !== null,
  );

  const count = (value: number | null | undefined, one: string, many: string, none: string) =>
    value === null || value === undefined ? (loading ? "Consultando…" : "Sin datos disponibles") : value === 0 ? none : `${value} ${value === 1 ? one : many}`;

  const opportunityTitles = new Map((data.opportunities ?? []).map((opportunity) => [opportunity.id, opportunity.title]));
  const studentPending: QueueItem[] = (data.studentRequirements ?? []).flatMap((status) => {
    const application = data.applications?.find((row) => row.placement_id === status.placement_id);
    return status.unmet.map((kind) => ({
      key: `${status.placement_id}-${kind}`,
      title: formatDomainLabel(kind),
      meta: application?.title ?? `Práctica ${status.placement_id}`,
      state: "REQUIRED",
    }));
  });
  const employerPending: QueueItem[] = (data.employerApplications ?? [])
    .filter((application) => application.state === "SUBMITTED")
    .map((application) => ({
      key: `app-${application.id}`,
      title: application.display_name,
      meta: `${opportunityTitles.get(application.opportunity_id) ?? "Oportunidad"} · ${application.program_code}`,
      state: application.state,
    }));
  const placementQueue = (rows: { id: number; state: string; display_name: string; program_code: string; opportunity_title: string }[] | null): QueueItem[] =>
    (rows ?? []).map((row) => ({ key: `p-${row.id}`, title: row.display_name, meta: `${row.opportunity_title} · ${row.program_code}`, state: row.state }));

  const summary: SummaryRow[] = [
    ...(isStudent ? [
      { label: "Mis postulaciones", value: data.applications?.length ?? null, action: "applications" as SectionId },
      { label: "Requisitos pendientes", value: studentUnmet, action: "documents" as SectionId },
    ] : []),
    ...(isEmployer ? [
      { label: "Oportunidades gestionadas", value: data.opportunities?.length ?? null, action: "opportunities" as SectionId },
      { label: "Candidaturas por revisar", value: pendingDecisions, action: "opportunities" as SectionId },
      { label: "Candidatos seleccionados", value: selectedCandidates },
    ] : []),
    ...(isAcademic ? [{ label: "Selecciones pendientes", value: data.academicQueue?.length ?? null, action: "academic" as SectionId }] : []),
    ...(isLegal ? [{ label: "Prácticas con documentos en cola", value: data.documentQueue?.length ?? null, action: "docreview" as SectionId }] : []),
    ...(isEc ? [{ label: "Prácticas en documentación", value: data.activationQueue?.length ?? null, action: "activation" as SectionId }] : []),
    ...(isAcademic || isWorkplaceSupervisor || isFacultySupervisor ? [{ label: isAcademic ? "Expedientes del programa" : "Prácticas vinculadas", value: data.visiblePlacements?.length ?? null, action: "dossier" as SectionId }] : []),
    { label: "Oportunidades visibles", value: data.opportunities?.length ?? null, action: "opportunities" as SectionId },
  ];

  const relatedPlacements = (title: string, description: string, buttonLabel: string, limit: number) => (
    <BentoCard variant="activity" className="dashboard-related-placements work-queue" title={title} description={description}>
      {relatedPlacementsState === "ready" ? (
        <ul className="queue-list activity-list">
          {data.visiblePlacements!.slice(0, limit).map((placement) => (
            <li key={placement.id}>
              <span className="queue-copy"><strong>{placement.opportunity_title}</strong><small>{placement.host_org_name} · {placement.program_code}</small></span>
              <Badge>{placement.state}</Badge>
            </li>
          ))}
        </ul>
      ) : relatedPlacementsState === "empty" ? <EmptyState message="No hay prácticas relacionadas para mostrar." />
        : relatedPlacementsState === "error" ? <p role="status" className="muted">No se pudo cargar la lista. Usa «Reintentar carga» en el aviso para volver a consultar.</p>
          : <Skeleton lines={3} />}
      <div className="queue-footer"><button className="btn secondary small" type="button" onClick={() => onNavigate("dossier")}>{buttonLabel}</button></div>
    </BentoCard>
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow={dashboardEyebrow}
        title={`Hola, ${user.display_name.split(" ")[0]}`}
        description={dashboardDescription}
      />

      {errors.map((error) => <Alert kind="error" key={error}>{error} <button className="btn link" type="button" onClick={() => setReloadAttempt((attempt) => attempt + 1)}>Reintentar carga</button></Alert>)}
      {loading && <div className="loading-line" role="status"><Spinner /> Actualizando tu espacio de trabajo…</div>}

      <div className={`dashboard-grid dashboard-grid--${dashboardVariant}`}>
        <div className="dashboard-main">
          {isStudent && (
            <>
              <BentoCard {...roleHero("student")} title="Siguiente paso" description={studentJourney.description}>
                <div className="hero-content">
                  <div>
                    <h2>{studentJourney.title}</h2>
                    {latestApplication && <p className="hero-record">Proceso más reciente · {latestApplication.title}</p>}
                    {studentJourney.state && <Badge>{studentJourney.state}</Badge>}
                  </div>
                  <button className="btn" type="button" disabled={studentJourney.disabled} onClick={() => onNavigate(studentJourney.action)}>{studentJourney.actionLabel}</button>
                </div>
              </BentoCard>
              {(studentPending.length > 0 || (data.studentRequirements !== null && !loading)) && (
                <WorkQueue title="Requisitos pendientes" description="Condiciones obligatorias que faltan en tus prácticas en documentación o activas."
                  items={studentPending} empty="No tienes requisitos pendientes." loading={loading}
                  action={{ label: "Abrir mis documentos", onClick: () => onNavigate("documents") }} />
              )}
              <BentoCard variant="activity" className="dashboard-activity work-queue" title="Actividad reciente" description="Tus postulaciones más recientes">
                {data.applications?.length ? (
                  <ul className="queue-list activity-list">
                    {data.applications.slice(0, 4).map((application) => (
                      <li key={application.id}>
                        <span className="queue-copy"><strong>{application.title}</strong><small>{application.placement_state ? formatDomainLabel(application.placement_state) : formatDomainLabel(application.state)}</small></span>
                        <Badge>{application.state}</Badge>
                      </li>
                    ))}
                  </ul>
                ) : data.applications && !loading ? <EmptyState message="Todavía no tienes postulaciones." action={<button className="btn secondary small" type="button" onClick={() => onNavigate("opportunities")}>Explorar oportunidades</button>} /> : <Skeleton lines={3} />}
              </BentoCard>
            </>
          )}

          {isEmployer && (
            <>
              <BentoCard {...roleHero("employer")} title="Candidaturas" description="El catálogo está limitado a las oportunidades visibles para tus relaciones registradas.">
                <div className="hero-content">
                  <div><h2>{count(pendingDecisions, "candidatura espera tu decisión", "candidaturas esperan tu decisión", "No hay candidaturas pendientes de decisión")}</h2><p className="hero-record">Las postulaciones muestran solo la información autorizada por el sistema.</p></div>
                  <button className="btn" type="button" onClick={() => onNavigate("opportunities")}>Gestionar oportunidades</button>
                </div>
              </BentoCard>
              <WorkQueue title="Candidaturas por decidir" description="Postulaciones enviadas a tus oportunidades." items={employerPending}
                empty="No hay candidaturas enviadas pendientes." loading={loading}
                action={{ label: "Abrir postulaciones", onClick: () => onNavigate("opportunities") }} />
            </>
          )}

          {isAcademic && (
            <>
              <BentoCard {...roleHero("academic")} title="Coordinación académica" description="Las selecciones se muestran según el programa asociado a tu cuenta.">
                <div className="hero-content">
                  <div><h2>{count(data.academicQueue?.length, "selección espera tu decisión", "selecciones esperan tu decisión", "No hay selecciones pendientes")}</h2><p className="hero-record">La aprobación fija las políticas vigentes para la práctica.</p></div>
                  <button className="btn" type="button" onClick={() => onNavigate("academic")}>Abrir revisión</button>
                </div>
              </BentoCard>
              <WorkQueue title="Selecciones por aprobar" description="Selecciones de organizaciones pendientes de decisión académica." items={placementQueue(data.academicQueue)}
                empty="No hay selecciones en tu cola académica." loading={loading}
                action={{ label: "Abrir revisión académica", onClick: () => onNavigate("academic") }} />
              {relatedPlacements("Expedientes del programa", "Solo prácticas vinculadas al programa de tu cuenta.", "Abrir expedientes", 5)}
            </>
          )}

          {(isWorkplaceSupervisor || isFacultySupervisor) && (
            <>
              <BentoCard
                {...roleHero("supervision")}
                title={isWorkplaceSupervisor ? "Supervisión laboral" : "Acompañamiento académico"}
                description={isWorkplaceSupervisor
                  ? "Consulta las prácticas y sus avances cuando la relación de supervisión está registrada."
                  : "Consulta los expedientes que tienen una asignación vigente a tu cuenta."}
              >
                <div className="hero-content">
                  <div>
                    <h2>{count(data.visiblePlacements?.length, "práctica vinculada", "prácticas vinculadas", "Sin prácticas vinculadas")}</h2>
                    <p className="hero-record">La información visible depende de las relaciones registradas para cada práctica.</p>
                  </div>
                  <button className="btn" type="button" onClick={() => onNavigate("dossier")}>Abrir expedientes</button>
                </div>
              </BentoCard>
              {!isAcademic && relatedPlacements("Prácticas vinculadas", "Expedientes según las relaciones de supervisión registradas para tu cuenta.", "Ver todas las prácticas", 6)}
            </>
          )}

          {isLegal && (
            <>
              <BentoCard {...roleHero("legal")} title="Revisión documental" description="La cola está limitada por los permisos de revisión de tu cuenta.">
                <div className="hero-content"><div><h2>{count(data.documentQueue?.length, "práctica con documentos por revisar", "prácticas con documentos por revisar", "No hay documentos por revisar")}</h2><p className="hero-record">Revisa cada archivo y registra el motivo de la decisión.</p></div><button className="btn" type="button" onClick={() => onNavigate("docreview")}>Abrir bandeja</button></div>
              </BentoCard>
              <WorkQueue title="Cola de revisión documental" description="Prácticas con entregas que esperan decisión." items={placementQueue(data.documentQueue)}
                empty="La cola documental está vacía." loading={loading}
                action={{ label: "Abrir revisión documental", onClick: () => onNavigate("docreview") }} />
            </>
          )}

          {isEc && (
            <>
              <BentoCard {...roleHero("experiential")} title="Activación de prácticas" description="El sistema calcula las condiciones y vuelve a validarlas antes de activar.">
                <div className="hero-content"><div><h2>{count(data.activationQueue?.length, "práctica en documentación", "prácticas en documentación", "No hay prácticas pendientes de activación")}</h2><p className="hero-record">Solo se activan las prácticas que cumplen todas las condiciones obligatorias.</p></div><button className="btn" type="button" onClick={() => onNavigate("activation")}>Abrir activaciones</button></div>
              </BentoCard>
              <WorkQueue title="Pendientes de activación" description="Prácticas en etapa de documentación." items={placementQueue(data.activationQueue)}
                empty="No hay prácticas en documentación." loading={loading}
                action={{ label: "Abrir activación", onClick: () => onNavigate("activation") }} />
            </>
          )}

          {!isStudent && !isEmployer && !isAcademic && !isLegal && !isEc && !isWorkplaceSupervisor && !isFacultySupervisor && (
            <BentoCard variant="hero" className="dashboard-hero" title="Acceso de solo lectura" description="Tu cuenta no tiene una vista de gestión asignada en la interfaz actual.">
              <div className="hero-content"><div><h2>Espacio de trabajo</h2><p className="hero-record">Las capacidades de supervisión y reportes no están implementadas en esta versión.</p></div></div>
            </BentoCard>
          )}
        </div>

        <aside className="dashboard-aside" aria-label="Resumen de tu espacio de trabajo">
          <section className="summary-panel" aria-labelledby="dashboard-summary-title">
            <h2 id="dashboard-summary-title">Resumen</h2>
            <dl className="summary-list">
              {summary.map((row) => (
                <div key={row.label}>
                  <dt>{row.action
                    ? <button className="summary-link" type="button" onClick={() => onNavigate(row.action!)}>{row.label}</button>
                    : row.label}</dt>
                  <dd>{row.value ?? (loading ? <span className="skeleton skeleton--inline" aria-label="Cargando" /> : "—")}</dd>
                </div>
              ))}
            </dl>
          </section>
          {isAcademic && (
            <section className="summary-panel" aria-labelledby="dashboard-policies-title">
              <h2 id="dashboard-policies-title">Políticas de programa</h2>
              <p className="muted">Consulta y crea versiones de las condiciones soportadas por el sistema.</p>
              <button className="btn secondary small" type="button" onClick={() => onNavigate("policies")}>Administrar políticas</button>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}

type QueueItem = { key: string; title: string; meta: string; state: string };
type SummaryRow = { label: string; value: number | null; action?: SectionId };

function WorkQueue({ title, description, items, empty, loading, action, limit = 5 }: {
  title: string;
  description: string;
  items: QueueItem[];
  empty: string;
  loading: boolean;
  action: { label: string; onClick: () => void };
  limit?: number;
}) {
  return (
    <BentoCard variant="task" className="work-queue" title={title} description={description}>
      {loading && items.length === 0 ? <Skeleton lines={3} />
        : items.length === 0 ? <EmptyState icon="check" message={empty} />
          : (
            <ul className="queue-list">
              {items.slice(0, limit).map((item) => (
                <li key={item.key}>
                  <span className="queue-copy"><strong>{item.title}</strong><small>{item.meta}</small></span>
                  <Badge>{item.state}</Badge>
                </li>
              ))}
            </ul>
          )}
      <div className="queue-footer">
        {items.length > limit && <span className="muted">{items.length - limit} más</span>}
        <button className="btn secondary small" type="button" onClick={action.onClick}>{action.label}</button>
      </div>
    </BentoCard>
  );
}
