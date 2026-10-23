import { useEffect, useState } from "react";
import * as api from "../api";
import type { ActivationStatus, Application, EmployerApplication, Opportunity, User } from "../api";
import { Alert, Badge, BentoCard, EmptyState, MetricCard, PageHeader, Spinner, formatDomainLabel } from "../components/ui";
import type { SectionId } from "../components/Layout";

type DashboardData = {
  opportunities: Opportunity[] | null;
  applications: Application[] | null;
  employerApplications: EmployerApplication[] | null;
  academicQueue: Awaited<ReturnType<typeof api.listPendingAcademic>> | null;
  documentQueue: Awaited<ReturnType<typeof api.listDocumentsPending>> | null;
  activationQueue: Awaited<ReturnType<typeof api.listPendingActivation>> | null;
  studentRequirements: ActivationStatus[] | null;
};

const emptyData: DashboardData = {
  opportunities: null,
  applications: null,
  employerApplications: null,
  academicQueue: null,
  documentQueue: null,
  activationQueue: null,
  studentRequirements: null,
};

export default function Dashboard({ user, onNavigate }: { user: User; onNavigate: (s: SectionId) => void }) {
  const [data, setData] = useState<DashboardData>(emptyData);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);

  const roles = user.roles.map((role) => role.role);
  const isStudent = roles.includes("STUDENT");
  const isEmployer = roles.includes("HOST_ORG_MEMBER");
  const isAcademic = roles.includes("PROGRAM_COORDINATOR");
  const isLegal = roles.includes("LEGAL_REVIEWER");
  const isEc = roles.includes("EXPERIENTIAL_COORDINATOR");

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

      const [opportunities, applications, academicQueue, documentQueue, activationQueue] = await Promise.all([
        capture("Oportunidades", () => api.listOpportunities()),
        isStudent ? capture("Postulaciones", () => api.listApplications()) : Promise.resolve(null),
        isAcademic ? capture("Revisión académica", () => api.listPendingAcademic()) : Promise.resolve(null),
        isLegal ? capture("Revisión documental", () => api.listDocumentsPending()) : Promise.resolve(null),
        isEc ? capture("Activaciones", () => api.listPendingActivation()) : Promise.resolve(null),
      ]);
      next.opportunities = opportunities;
      next.applications = applications;
      next.academicQueue = academicQueue;
      next.documentQueue = documentQueue;
      next.activationQueue = activationQueue;

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
  }, [isStudent, isEmployer, isAcademic, isLegal, isEc]);

  const latestApplication = data.applications?.[0];
  const pendingDecisions = data.employerApplications?.filter((application) => application.state === "SUBMITTED").length ?? null;
  const selectedCandidates = data.employerApplications?.filter((application) => application.placement_id !== null).length ?? null;
  const studentUnmet = data.studentRequirements?.reduce((total, status) => total + status.unmet.length, 0) ?? null;

  let studentHeadline = "Encuentra una oportunidad para tu práctica";
  let studentDescription = "Explora el catálogo y revisa las condiciones de elegibilidad antes de postularte.";
  let studentAction: SectionId = "opportunities";
  let studentActionLabel = "Explorar oportunidades";
  if (latestApplication?.placement_state === "ACTIVE") {
    studentHeadline = "Tu práctica está activa";
    studentDescription = "Consulta el estado de tus documentos y los requisitos asociados a tu colocación.";
    studentAction = "documents";
    studentActionLabel = "Consultar documentos";
  } else if (latestApplication?.placement_state === "DOCUMENTATION_PENDING") {
    studentHeadline = "Completa la documentación de tu práctica";
    studentDescription = "La activación depende de que se aprueben los requisitos obligatorios.";
    studentAction = "documents";
    studentActionLabel = "Revisar requisitos";
  } else if (latestApplication?.placement_state === "PENDING_ACADEMIC_APPROVAL") {
    studentHeadline = "Tu selección está en revisión académica";
    studentDescription = "La coordinación del programa debe aprobar la selección antes de iniciar la etapa documental.";
    studentAction = "applications";
    studentActionLabel = "Ver mi postulación";
  } else if (latestApplication?.state === "SELECTED") {
    studentHeadline = "Has sido seleccionado";
    studentDescription = "Consulta el estado de la postulación mientras se registra la práctica resultante.";
    studentAction = "applications";
    studentActionLabel = "Ver mi postulación";
  } else if (data.applications?.length) {
    studentHeadline = "Sigue el estado de tus postulaciones";
    studentDescription = "Las decisiones y el estado de cada práctica aparecen en tu historial.";
    studentAction = "applications";
    studentActionLabel = "Ver mis postulaciones";
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="TU RESUMEN"
        title={`Hola, ${user.display_name.split(" ")[0]}`}
        description="Un espacio de trabajo con el estado de tus procesos y las acciones disponibles para tu rol."
      />

      {errors.map((error) => <Alert kind="error" key={error}>{error}</Alert>)}
      {loading && <div className="loading-line"><Spinner /> Actualizando tu espacio de trabajo…</div>}

      <div className="bento-grid dashboard-grid">
        {isStudent && (
          <>
            <BentoCard variant="hero" className="dashboard-hero" icon="01" title="Siguiente paso" description={studentDescription}>
              <div className="hero-content">
                <div>
                  <h2>{studentHeadline}</h2>
                  {latestApplication && <p className="hero-record">Proceso más reciente · {latestApplication.title}</p>}
                  {latestApplication?.placement_state && <Badge>{latestApplication.placement_state}</Badge>}
                </div>
                <button className="btn" type="button" onClick={() => onNavigate(studentAction)}>{studentActionLabel}<span aria-hidden="true">↗</span></button>
              </div>
            </BentoCard>
            <MetricCard label="Mis postulaciones" value={data.applications?.length ?? null} detail="En el historial de tu cuenta" icon="02" />
            <MetricCard label="Requisitos pendientes" value={studentUnmet} detail="En prácticas con checklist" icon="03" />
            <BentoCard variant="action" className="dashboard-opportunities" icon="↗" title="Catálogo de oportunidades" description="Consulta las oportunidades publicadas que puedes ver con tu cuenta.">
              <div className="action-card-bottom">
                <span className="action-count">{data.opportunities?.length ?? "—"} <small>visibles</small></span>
                <button className="btn secondary" type="button" onClick={() => onNavigate("opportunities")}>Abrir catálogo</button>
              </div>
            </BentoCard>
            <BentoCard variant="activity" className="dashboard-activity" icon="04" title="Actividad reciente" description="Tus postulaciones más recientes">
              {data.applications?.length ? (
                <ul className="activity-list">
                  {data.applications.slice(0, 3).map((application) => (
                    <li key={application.id}>
                      <span className="activity-dot" aria-hidden="true" />
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
            <BentoCard variant="hero" className="dashboard-hero" icon="01" title="Gestión de oportunidades" description="El catálogo está limitado a las oportunidades visibles para tus relaciones registradas.">
              <div className="hero-content">
                <div><h2>Revisa tus candidaturas</h2><p className="hero-record">Las postulaciones muestran la información autorizada por el sistema.</p></div>
                <button className="btn" type="button" onClick={() => onNavigate("opportunities")}>Gestionar oportunidades<span aria-hidden="true">↗</span></button>
              </div>
            </BentoCard>
            <MetricCard label="Oportunidades gestionadas" value={data.opportunities?.length ?? null} detail="Según el alcance de tu cuenta" icon="02" />
            <MetricCard label="Candidaturas por revisar" value={pendingDecisions} detail="Postulaciones enviadas" icon="03" />
            <MetricCard label="Candidatos seleccionados" value={selectedCandidates} detail="Con práctica registrada" icon="04" />
            <BentoCard variant="action" className="dashboard-opportunities" icon="↗" title="Acceso a la bandeja" description={pendingDecisions === null ? "Abre una oportunidad para consultar su bandeja de postulaciones." : pendingDecisions ? `${pendingDecisions} candidaturas esperan una decisión.` : "No hay candidaturas pendientes de decisión."}>
              <button className="btn secondary" type="button" onClick={() => onNavigate("opportunities")}>Abrir postulaciones</button>
            </BentoCard>
          </>
        )}

        {isAcademic && (
          <>
            <BentoCard variant="hero" className="dashboard-hero" icon="01" title="Coordinación académica" description="Las selecciones se muestran según el programa asociado a tu cuenta.">
              <div className="hero-content">
                <div><h2>{data.academicQueue?.length ? "Hay selecciones por revisar" : "Revisa tu cola académica"}</h2><p className="hero-record">La aprobación fija las políticas vigentes para la colocación.</p></div>
                <button className="btn" type="button" onClick={() => onNavigate("academic")}>Abrir revisión<span aria-hidden="true">↗</span></button>
              </div>
            </BentoCard>
            <MetricCard label="Selecciones pendientes" value={data.academicQueue?.length ?? null} detail="En tu alcance académico" icon="02" />
            <BentoCard variant="action" className="dashboard-opportunities" icon="03" title="Políticas de programa" description="Consulta y crea versiones de las condiciones soportadas por la API.">
              <button className="btn secondary" type="button" onClick={() => onNavigate("policies")}>Administrar políticas</button>
            </BentoCard>
          </>
        )}

        {isLegal && (
          <>
            <BentoCard variant="hero" className="dashboard-hero" icon="01" title="Revisión documental" description="La cola está limitada por los permisos de revisión de tu cuenta.">
              <div className="hero-content"><div><h2>Documentos que requieren atención</h2><p className="hero-record">Revisa cada archivo y registra el motivo de la decisión.</p></div><button className="btn" type="button" onClick={() => onNavigate("docreview")}>Abrir bandeja<span aria-hidden="true">↗</span></button></div>
            </BentoCard>
            <MetricCard label="Prácticas en la cola" value={data.documentQueue?.length ?? null} detail="Con documentos para revisar" icon="02" />
          </>
        )}

        {isEc && (
          <>
            <BentoCard variant="hero" className="dashboard-hero" icon="01" title="Activación de prácticas" description="La API calcula las condiciones y bloquea cualquier activación que no esté lista.">
              <div className="hero-content"><div><h2>Comprueba las compuertas</h2><p className="hero-record">La acción de activar sigue sujeta a la validación del servidor.</p></div><button className="btn" type="button" onClick={() => onNavigate("activation")}>Abrir activaciones<span aria-hidden="true">↗</span></button></div>
            </BentoCard>
            <MetricCard label="En documentación" value={data.activationQueue?.length ?? null} detail="Prácticas pendientes de activación" icon="02" />
          </>
        )}

        {!isStudent && !isEmployer && !isAcademic && !isLegal && !isEc && (
          <BentoCard variant="hero" className="dashboard-hero" icon="01" title="Acceso de solo lectura" description="Tu cuenta no tiene una vista de gestión asignada en la interfaz actual.">
            <div className="hero-content"><div><h2>Espacio de trabajo</h2><p className="hero-record">Las capacidades de supervisión y reportes no están implementadas en esta versión.</p></div></div>
          </BentoCard>
        )}
      </div>
    </div>
  );
}
