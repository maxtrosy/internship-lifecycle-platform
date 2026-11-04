import { useEffect, useState } from "react";
import * as api from "../api";
import type { ActivationStatus, Application, EmployerApplication, Opportunity, User } from "../api";
import type { VisiblePlacement } from "../api";
import { Alert, Badge, BentoCard, EmptyState, MetricCard, PageHeader, Spinner, formatDomainLabel } from "../components/ui";
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
  const dashboardVariant = isStudent ? "student" : isEmployer ? "employer" : isAcademic ? "academic" : isLegal ? "legal" : isEc ? "experiential" : "limited";

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

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="TU RESUMEN"
        title={`Hola, ${user.display_name.split(" ")[0]}`}
        description="Un espacio de trabajo con el estado de tus procesos y las acciones disponibles para tu rol."
      />

      {errors.map((error) => <Alert kind="error" key={error}>{error} <button className="btn link" type="button" onClick={() => setReloadAttempt((attempt) => attempt + 1)}>Reintentar carga</button></Alert>)}
      {loading && <div className="loading-line"><Spinner /> Actualizando tu espacio de trabajo…</div>}

      <div className={`bento-grid dashboard-grid dashboard-grid--${dashboardVariant}`}>
        {isStudent && (
          <>
            <BentoCard variant="hero" className="dashboard-hero" title="Siguiente paso" description={studentJourney.description}>
              <div className="hero-content">
                <div>
                  <h2>{studentJourney.title}</h2>
                  {latestApplication && <p className="hero-record">Proceso más reciente · {latestApplication.title}</p>}
                  {studentJourney.state && <Badge>{studentJourney.state}</Badge>}
                </div>
                <button className="btn" type="button" disabled={studentJourney.disabled} onClick={() => onNavigate(studentJourney.action)}>{studentJourney.actionLabel}<span aria-hidden="true">→</span></button>
              </div>
            </BentoCard>
            <MetricCard label="Mis postulaciones" value={data.applications?.length ?? null} detail="En el historial de tu cuenta" />
            <MetricCard label="Requisitos pendientes" value={studentUnmet} detail="En tus prácticas" />
            <BentoCard variant="action" className="dashboard-opportunities" title="Catálogo de oportunidades" description="Consulta las oportunidades publicadas que puedes ver con tu cuenta.">
              <div className="action-card-bottom">
                <span className="action-count">{data.opportunities?.length ?? "—"} <small>visibles</small></span>
                <button className="btn secondary" type="button" onClick={() => onNavigate("opportunities")}>Abrir catálogo</button>
              </div>
            </BentoCard>
            <BentoCard variant="activity" className="dashboard-activity" title="Actividad reciente" description="Tus postulaciones más recientes">
              {data.applications?.length ? (
                <ul className="activity-list">
                  {data.applications.slice(0, 3).map((application) => (
                    <li key={application.id}>
                      <span className="activity-copy"><strong>{application.title}</strong><small>{application.placement_state ? formatDomainLabel(application.placement_state) : formatDomainLabel(application.state)}</small></span>
                      <Badge>{application.state}</Badge>
                    </li>
                  ))}
                </ul>
              ) : data.applications && !loading ? <EmptyState message="Todavía no tienes postulaciones." /> : null}
            </BentoCard>
          </>
        )}

        {isEmployer && (
          <>
            <BentoCard variant="hero" className="dashboard-hero" title="Gestión de oportunidades" description="El catálogo está limitado a las oportunidades visibles para tus relaciones registradas.">
              <div className="hero-content">
                <div><h2>Revisa tus candidaturas</h2><p className="hero-record">Las postulaciones muestran la información autorizada por el sistema.</p></div>
                <button className="btn" type="button" onClick={() => onNavigate("opportunities")}>Gestionar oportunidades<span aria-hidden="true">→</span></button>
              </div>
            </BentoCard>
            <MetricCard label="Oportunidades gestionadas" value={data.opportunities?.length ?? null} detail="Según el alcance de tu cuenta" />
            <MetricCard label="Candidaturas por revisar" value={pendingDecisions} detail="Postulaciones enviadas" />
            <MetricCard label="Candidatos seleccionados" value={selectedCandidates} detail="Con práctica registrada" />
            <BentoCard variant="action" className="dashboard-opportunities" title="Acceso a la bandeja" description={pendingDecisions === null ? "Abre una oportunidad para consultar su bandeja de postulaciones." : pendingDecisions ? `${pendingDecisions} candidaturas esperan una decisión.` : "No hay candidaturas pendientes de decisión."}>
              <button className="btn secondary" type="button" onClick={() => onNavigate("opportunities")}>Abrir postulaciones</button>
            </BentoCard>
          </>
        )}

        {isAcademic && (
          <>
            <BentoCard variant="hero" className="dashboard-hero" title="Coordinación académica" description="Las selecciones se muestran según el programa asociado a tu cuenta.">
              <div className="hero-content">
                <div><h2>{data.academicQueue?.length ? "Hay selecciones por revisar" : "Revisa tu cola académica"}</h2><p className="hero-record">La aprobación fija las políticas vigentes para la colocación.</p></div>
                <button className="btn" type="button" onClick={() => onNavigate("academic")}>Abrir revisión<span aria-hidden="true">→</span></button>
              </div>
            </BentoCard>
            <MetricCard label="Selecciones pendientes" value={data.academicQueue?.length ?? null} detail="En tu alcance académico" />
            <BentoCard variant="action" className="dashboard-opportunities" title="Políticas de programa" description="Consulta y crea versiones de las condiciones soportadas por el sistema.">
              <button className="btn secondary" type="button" onClick={() => onNavigate("policies")}>Administrar políticas</button>
            </BentoCard>
            <BentoCard variant="activity" className="dashboard-related-placements" title="Expedientes del programa" description="La lista incluye solo prácticas vinculadas al programa de tu cuenta.">
              {relatedPlacementsState === "ready" ? (
                <ul className="activity-list">
                  {data.visiblePlacements!.slice(0, 4).map((placement) => (
                    <li key={placement.id}>
                      <span className="activity-copy"><strong>{placement.opportunity_title}</strong><small>{placement.program_code} · {formatDomainLabel(placement.state)}</small></span>
                      <Badge>{placement.state}</Badge>
                    </li>
                  ))}
                </ul>
              ) : relatedPlacementsState === "empty" ? <EmptyState message="No hay prácticas relacionadas para mostrar." />
                : relatedPlacementsState === "error" ? <p role="status" className="muted">No se pudo cargar la lista. Usa «Reintentar carga» en el aviso para volver a consultar.</p>
                  : null}
              <button className="btn secondary" type="button" onClick={() => onNavigate("dossier")}>Abrir expedientes</button>
            </BentoCard>
          </>
        )}

        {(isWorkplaceSupervisor || isFacultySupervisor) && (
          <>
            <MetricCard label="Prácticas vinculadas" value={data.visiblePlacements?.length ?? null} detail="Según las relaciones de supervisión" />
            <BentoCard variant="activity" className="dashboard-related-placements" title="Prácticas vinculadas" description="Los expedientes aparecen según las relaciones de supervisión registradas para tu cuenta.">
              {relatedPlacementsState === "ready" ? (
                <ul className="activity-list">
                  {data.visiblePlacements!.slice(0, 5).map((placement) => (
                    <li key={placement.id}>
                      <span className="activity-copy"><strong>{placement.opportunity_title}</strong><small>{placement.program_code} · {formatDomainLabel(placement.state)}</small></span>
                      <Badge>{placement.state}</Badge>
                    </li>
                  ))}
                </ul>
              ) : relatedPlacementsState === "empty" ? <EmptyState message="No hay prácticas vinculadas actualmente." />
                : relatedPlacementsState === "error" ? <p role="status" className="muted">No se pudo cargar la lista. Usa «Reintentar carga» en el aviso para volver a consultar.</p>
                  : <div className="loading-line"><Spinner /> Consultando relaciones…</div>}
              <button className="btn secondary" type="button" onClick={() => onNavigate("dossier")}>Abrir expedientes</button>
            </BentoCard>
          </>
        )}

        {isLegal && (
          <>
            <BentoCard variant="hero" className="dashboard-hero" title="Revisión documental" description="La cola está limitada por los permisos de revisión de tu cuenta.">
              <div className="hero-content"><div><h2>Documentos que requieren atención</h2><p className="hero-record">Revisa cada archivo y registra el motivo de la decisión.</p></div><button className="btn" type="button" onClick={() => onNavigate("docreview")}>Abrir bandeja<span aria-hidden="true">→</span></button></div>
            </BentoCard>
            <MetricCard label="Prácticas en la cola" value={data.documentQueue?.length ?? null} detail="Con documentos para revisar" />
          </>
        )}

        {isEc && (
          <>
            <BentoCard variant="hero" className="dashboard-hero" title="Activación de prácticas" description="El sistema calcula las condiciones y vuelve a validarlas antes de activar.">
              <div className="hero-content"><div><h2>Comprueba las condiciones</h2><p className="hero-record">La práctica solo se podrá activar cuando cumpla todas las condiciones.</p></div><button className="btn" type="button" onClick={() => onNavigate("activation")}>Abrir activaciones<span aria-hidden="true">→</span></button></div>
            </BentoCard>
            <MetricCard label="En documentación" value={data.activationQueue?.length ?? null} detail="Prácticas pendientes de activación" />
          </>
        )}

        {!isStudent && !isEmployer && !isAcademic && !isLegal && !isEc && !isWorkplaceSupervisor && !isFacultySupervisor && (
          <BentoCard variant="hero" className="dashboard-hero" title="Acceso de solo lectura" description="Tu cuenta no tiene una vista de gestión asignada en la interfaz actual.">
            <div className="hero-content"><div><h2>Espacio de trabajo</h2><p className="hero-record">Las capacidades de supervisión y reportes no están implementadas en esta versión.</p></div></div>
          </BentoCard>
        )}
      </div>
    </div>
  );
}
