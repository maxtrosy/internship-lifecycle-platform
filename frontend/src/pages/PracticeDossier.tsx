import { useEffect, useRef, useState } from "react";
import * as api from "../api";
import type { DocumentSubmission, PlacementDossier, VisiblePlacement } from "../api";
import type { User } from "../api";
import type { SectionId } from "../components/Layout";
import ActivityTimeline from "../components/ActivityTimeline";
import PlacementFollowUp from "../components/PlacementFollowUp";
import PlacementWorkPlan from "../components/PlacementWorkPlan";
import PlacementMessages from "../components/PlacementMessages";
import FacultyAssignmentManager from "../components/FacultyAssignmentManager";
import PlacementSegments from "../components/PlacementSegments";
import HoursReviewList from "../components/HoursReviewList";
import { DossierSectionNav, HoursProgress, LifecycleSteps, SituationPanel, type Situation } from "../components/DossierOverview";
import { DisabledReason } from "../components/overlays";
import { segmentGateBlockers } from "../segments";
import { Alert, Badge, BentoCard, EmptyState, PageHeader, Spinner, formatDomainLabel } from "../components/ui";
import { completionRequirementsSatisfied } from "../completion";
import { canDisplayDossierHours } from "../dossier";
import { formatCalendarDate, formatHistoryDate } from "../history";

type Props = { user: User; onNavigate: (section: SectionId) => void };

function localDate(value: string | null | undefined): string {
  return formatCalendarDate(value);
}

function hoursLabel(value: number | string | null): string {
  if (value === null) return "—";
  const numeric = Number(value);
  return Number.isFinite(numeric) ? new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 }).format(numeric) : "—";
}

function completionBlocker(dossier: PlacementDossier): string | null {
  if (!dossier.completion_requirements_configured) {
    return "No hay una política de finalización fijada para este expediente.";
  }
  if (dossier.completion_requirements === null) {
    return "Los requisitos no están disponibles para este rol.";
  }
  if (dossier.placement.activation_unmet.length > 0) {
    return `Requisitos de activación pendientes: ${dossier.placement.activation_unmet.map(formatDomainLabel).join(", ")}.`;
  }
  const unmet = dossier.completion_requirements.filter((item) => item.mandatory && !item.satisfied);
  if (unmet.length) {
    return `Requisitos de finalización pendientes: ${unmet.map((item) => formatDomainLabel(item.kind)).join(", ")}.`;
  }
  // CR-05-BR-07: segment-level conditions (open segments, unreviewed hours, combined review).
  const segmentBlockers = segmentGateBlockers(dossier.segment_gate, dossier.placement.state === "ACTIVE");
  return segmentBlockers.length ? `Pendiente en segmentos: ${segmentBlockers.join("; ")}.` : null;
}

/** Current situation for the dossier header: what blocks progress, or what comes next. */
function situationFor(dossier: PlacementDossier): Situation {
  const state = dossier.placement.state;
  if (state === "PENDING_ACADEMIC_APPROVAL") {
    return { tone: "info", title: "Pendiente de aprobación académica", detail: "La coordinación del programa debe aprobar o rechazar la selección antes de iniciar la documentación." };
  }
  if (state === "DOCUMENTATION_PENDING") {
    if (dossier.placement.activation_unmet.length) {
      return { tone: "blocked", title: "Bloqueos para activar", detail: `Falta: ${dossier.placement.activation_unmet.map(formatDomainLabel).join(", ")}.` };
    }
    return { tone: "ready", title: "Lista para activar", detail: "Las condiciones obligatorias están satisfechas; la activación corresponde a la coordinación de prácticas." };
  }
  if (state === "ACTIVE") {
    const blocker = completionBlocker(dossier);
    return blocker
      ? { tone: "blocked", title: "Pendiente para finalizar", detail: blocker }
      : { tone: "ready", title: "Requisitos de finalización cumplidos", detail: "La finalización puede confirmarse; el backend vuelve a comprobar los requisitos." };
  }
  if (state === "COMPLETED") {
    const blocker = completionBlocker(dossier);
    return { tone: blocker ? "blocked" : "ready", title: "Finalización confirmada · pendiente de cierre", detail: blocker ?? "El cierre deja el expediente como registro histórico." };
  }
  if (state === "CLOSED") {
    return { tone: "done", title: "Práctica cerrada", detail: "El expediente se conserva como registro histórico con su actividad completa." };
  }
  return { tone: "info", title: formatDomainLabel(state), detail: "Consulta el historial para ver la última decisión registrada." };
}

export default function PracticeDossier({ user, onNavigate }: Props) {
  const [placements, setPlacements] = useState<VisiblePlacement[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [dossier, setDossier] = useState<PlacementDossier | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [detailAttempt, setDetailAttempt] = useState(0);
  const [completionAction, setCompletionAction] = useState<"confirm" | "close" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const detailRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let current = true;
    setListLoading(true);
    setError(null);
    api.listVisiblePlacements()
      .then((rows) => {
        if (!current) return;
        setPlacements(rows);
        const requested = Number(sessionStorage.getItem("dh05:open-placement"));
        const requestedIsVisible = Number.isInteger(requested) && rows.some((row) => row.id === requested);
        if (requestedIsVisible) sessionStorage.removeItem("dh05:open-placement");
        setSelectedId((id) => requestedIsVisible ? requested : id !== null && rows.some((row) => row.id === id) ? id : rows[0]?.id ?? null);
      })
      .catch((err: unknown) => {
        if (current) setError(err instanceof Error ? err.message : "No fue posible cargar los expedientes.");
      })
      .finally(() => { if (current) setListLoading(false); });
    return () => { current = false; };
  }, [attempt]);

  useEffect(() => {
    if (selectedId === null) { setDossier(null); return; }
    let current = true;
    setDetailLoading(true);
    setError(null);
    setDossier(null);
    api.getPlacementDossier(selectedId)
      .then((record) => { if (current) setDossier(record); })
      .catch((err: unknown) => {
        if (current) setError(err instanceof Error ? err.message : "No fue posible cargar el expediente.");
      })
      .finally(() => { if (current) setDetailLoading(false); });
    return () => { current = false; };
  }, [selectedId, detailAttempt]);

  async function download(itemId: number, submission: DocumentSubmission) {
    if (selectedId === null) return;
    setError(null);
    try {
      await api.downloadDocument(selectedId, itemId, submission);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible descargar el documento.");
    }
  }

  async function runCompletionAction(action: "confirm" | "close") {
    if (selectedId === null) return;
    setCompletionAction(action);
    setError(null);
    setNotice(null);
    try {
      if (action === "confirm") await api.confirmPlacementCompletion(selectedId);
      else await api.closePlacement(selectedId);
      setNotice(action === "confirm" ? "Finalización confirmada." : "Práctica cerrada.");
      setAttempt((value) => value + 1);
      setDetailAttempt((value) => value + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible actualizar el cierre de la práctica.");
    } finally {
      setCompletionAction(null);
    }
  }

  const selectedRow = placements?.find((row) => row.id === selectedId);
  const roles = user.roles.map((role) => role.role);
  const eligibleResult = dossier?.application.eligibility_result;
  const showDossierHours = dossier
    ? canDisplayDossierHours(dossier.capabilities.read_hours, dossier.hours)
    : false;
  const activationWasRecorded = dossier !== null && ["ACTIVE", "COMPLETED", "CLOSED"].includes(dossier.placement.state);
  const hasHeroActions = dossier !== null && (
    dossier.capabilities.activate || dossier.capabilities.submit_documents || dossier.capabilities.record_hours
    || dossier.capabilities.review_documents
    || (dossier.capabilities.decide_academically && dossier.placement.state === "PENDING_ACADEMIC_APPROVAL"));

  return (
    <div className="page-stack dossier-page">
      <PageHeader eyebrow="Ciclo de vida" title="Expediente de práctica" description="Consulta el recorrido persistido de cada práctica. Los documentos, horas y acciones disponibles dependen de tu relación y permisos." />
      {error && <Alert kind="error">{error} <button className="btn link" type="button" onClick={() => {
        setAttempt((value) => value + 1);
        setDetailAttempt((value) => value + 1);
      }}>Reintentar</button></Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}
      {listLoading && <div className="empty"><Spinner /> Cargando prácticas…</div>}
      {!listLoading && placements?.length === 0 && <EmptyState message="No hay prácticas relacionadas con tu cuenta." />}
      {!listLoading && placements && placements.length > 0 && (
        <div className={`dossier-layout${placements.length === 1 ? " dossier-layout--single" : ""}`}>
          {placements.length > 1 && <BentoCard variant="content" className="dossier-index" title="Prácticas visibles" description={`${placements.length} expedientes según tus relaciones actuales`}>
            <ul className="dossier-list" aria-label="Prácticas disponibles">
              {placements.map((row) => (
                <li key={row.id}>
                  <button
                    type="button"
                    className={`dossier-list-item ${row.id === selectedId ? "selected" : ""}`}
                    aria-current={row.id === selectedId ? "true" : undefined}
                    onClick={() => setSelectedId(row.id)}
                  >
                    <span className="dossier-list-title">{row.opportunity_title}</span>
                    <span className="dossier-list-meta">{row.host_org_name} · {row.program_code}</span>
                    <span className="dossier-list-state"><Badge>{row.state}</Badge></span>
                  </button>
                </li>
              ))}
            </ul>
          </BentoCard>}

          {detailLoading && <div className="empty dossier-detail-loading"><Spinner /> Cargando expediente…</div>}
          {dossier && selectedRow && (
            <div className="dossier-detail" key={dossier.placement.id} ref={detailRef}>
              <BentoCard variant="hero" className="dossier-hero">
                <div className="dossier-hero-heading">
                  <div>
                    <p className="dossier-hero-kicker">Expediente n.º {dossier.placement.id}</p>
                    <h2>{dossier.opportunity.title}</h2>
                    <p>{dossier.opportunity.host_org_name} · {dossier.opportunity.program_name} ({dossier.opportunity.program_code})</p>
                  </div>
                  <Badge>{dossier.placement.state}</Badge>
                </div>
                <dl className="dossier-hero-grid">
                  <div><dt>Estudiante</dt><dd>{dossier.student.display_name}</dd></div>
                  <div><dt>Postulación</dt><dd><Badge>{dossier.application.state}</Badge></dd></div>
                  <div><dt>Elegibilidad · política {dossier.application.eligibility_policy_version === null ? "no registrada" : `v${dossier.application.eligibility_policy_version}`}</dt><dd><Badge state={eligibleResult ?? "UNKNOWN"}>{eligibleResult ? formatDomainLabel(eligibleResult) : "No disponible"}</Badge></dd></div>
                  <div><dt>Supervisor laboral vigente</dt><dd>{dossier.current_version?.workplace_supervisor_name ?? "Sin asignación registrada"}</dd></div>
                </dl>
                <LifecycleSteps state={dossier.placement.state} />
                <div className="dossier-hero-status">
                  <SituationPanel situation={situationFor(dossier)} />
                  {showDossierHours && <HoursProgress dossier={dossier} />}
                </div>
                {hasHeroActions && (
                  <div className="dossier-hero-actions">
                    {dossier.capabilities.activate && <button className="btn" type="button" onClick={() => onNavigate("activation")}>Abrir activación</button>}
                    {dossier.capabilities.decide_academically && dossier.placement.state === "PENDING_ACADEMIC_APPROVAL" && <button className="btn" type="button" onClick={() => onNavigate("academic")}>Abrir revisión académica</button>}
                    {(dossier.capabilities.submit_documents || dossier.capabilities.record_hours) && <button className="btn secondary" type="button" onClick={() => onNavigate("documents")}>Abrir mis documentos y horas</button>}
                    {dossier.capabilities.review_documents && <button className="btn secondary" type="button" onClick={() => onNavigate("docreview")}>Abrir revisión documental</button>}
                  </div>
                )}
              </BentoCard>

              <DossierSectionNav containerRef={detailRef} version={`${dossier.placement.id}-${detailAttempt}`} />

              <div className="dossier-grid">
                <section className="dossier-section dossier-group--split" id={`dossier-${dossier.placement.id}-requirements`} data-dossier-section="Requisitos" tabIndex={-1}>
                  <BentoCard variant="content" title="Condiciones para activar" description={dossier.activation_policy_version ? `Política de activación v${dossier.activation_policy_version}` : "Condiciones persistidas por el flujo de aprobación académica"}>
                    {!dossier.placement.activation_requirements_instantiated && <Alert kind="info">Las condiciones se instancian al aprobar académicamente la selección.</Alert>}
                    {dossier.placement.activation_requirements_instantiated && dossier.activation_requirements.length === 0 && <EmptyState message="No hay requisitos de activación instanciados." />}
                    {dossier.activation_requirements.length > 0 && <ul className="requirement-list">
                      {dossier.activation_requirements.map((item) => (
                        <li className="dossier-requirement" key={item.id}>
                          <span>{formatDomainLabel(item.kind)}{item.mandatory ? " · obligatorio" : " · opcional"}</span><Badge>{item.status}</Badge>
                        </li>
                      ))}
                    </ul>}
                    {dossier.placement.activation_requirements_instantiated && (
                      <p className="dossier-gate-note">{dossier.placement.activation_ready
                        ? "Condiciones obligatorias satisfechas; la activación permanece a cargo del rol autorizado."
                        : dossier.placement.activation_unmet.length
                          ? `Pendiente: ${dossier.placement.activation_unmet.map(formatDomainLabel).join(", ")}.`
                          : activationWasRecorded
                            ? "La activación se registró y no hay requisitos pendientes en la proyección."
                            : "La práctica aún no está en etapa de activación."}</p>
                    )}
                  </BentoCard>

                  <BentoCard variant="content" title="Progreso y finalización" description={dossier.completion_policy_version ? `Política de finalización v${dossier.completion_policy_version}` : "Condiciones fijadas para este expediente"}>
                    {showDossierHours && (
                      <div className="dossier-hours-summary"><span>Horas reportadas</span><strong>{hoursLabel(dossier.hours_total)} h</strong>
                        {dossier.hours_summary && <span className="muted"> · aceptadas {hoursLabel(dossier.hours_summary.accepted_total)} h</span>}</div>
                    )}
                    {!dossier.completion_requirements_configured && <p className="muted">La política de finalización se fija durante la aprobación académica.</p>}
                    {dossier.completion_requirements_configured && dossier.completion_requirements === null && <p className="muted">Los detalles de finalización no están disponibles para este rol.</p>}
                    {dossier.completion_requirements?.length === 0 && <EmptyState message="La política fijada no contiene requisitos de finalización." />}
                    {!!dossier.completion_requirements?.length && <ul className="requirement-list">
                      {dossier.completion_requirements.map((item) => (
                        <li className="dossier-requirement" key={item.kind}>
                          <span>{formatDomainLabel(item.kind)}{item.threshold !== null ? ` · ${hoursLabel(item.threshold)} h` : ""}{item.mandatory ? " · obligatorio" : " · opcional"}</span>
                          <Badge state={item.satisfied ? "APPROVED" : "REQUIRED"}>{item.satisfied ? "Cumplido" : "Pendiente"}</Badge>
                        </li>
                      ))}
                    </ul>}
                    {dossier.completion_requirements_configured && dossier.completion_requirements && dossier.completion_requirements.length > 0 && <p className="muted">Las horas mínimas se calculan con horas aceptadas por el rol revisor configurado, no con horas reportadas.</p>}
                    {dossier.placement.state === "CLOSED" && <Alert kind="success">La práctica quedó cerrada.</Alert>}
                    {dossier.capabilities.confirm_completion && dossier.placement.state === "ACTIVE" && (() => {
                      const ready = completionRequirementsSatisfied(
                        dossier.completion_requirements_configured,
                        dossier.completion_requirements,
                      ) && dossier.placement.activation_unmet.length === 0
                        && segmentGateBlockers(dossier.segment_gate, true).length === 0;
                      const blocker = completionBlocker(dossier);
                      const noteId = `completion-note-${dossier.placement.id}`;
                      return (
                        <div className="dossier-completion-actions">
                          {blocker
                            ? <DisabledReason id={noteId}>{blocker}</DisabledReason>
                            : <p id={noteId} className="dossier-gate-note">La confirmación vuelve a comprobar en backend los requisitos persistidos.</p>}
                          <button className="btn" type="button" disabled={!ready || completionAction !== null} aria-describedby={noteId}
                            onClick={() => void runCompletionAction("confirm")}>
                            {completionAction === "confirm" ? "Confirmando…" : "Confirmar finalización"}
                          </button>
                        </div>
                      );
                    })()}
                    {dossier.capabilities.close_placement && dossier.placement.state === "COMPLETED" && (() => {
                      const ready = completionRequirementsSatisfied(
                        dossier.completion_requirements_configured,
                        dossier.completion_requirements,
                      ) && dossier.placement.activation_unmet.length === 0;
                      const blocker = completionBlocker(dossier);
                      const noteId = `close-note-${dossier.placement.id}`;
                      return (
                        <div className="dossier-completion-actions">
                          {blocker
                            ? <DisabledReason id={noteId}>{blocker}</DisabledReason>
                            : <p id={noteId} className="dossier-gate-note">El cierre vuelve a comprobar en backend los requisitos persistidos.</p>}
                          <button className="btn" type="button" disabled={!ready || completionAction !== null} aria-describedby={noteId}
                            onClick={() => void runCompletionAction("close")}>
                            {completionAction === "close" ? "Cerrando…" : "Cerrar práctica"}
                          </button>
                        </div>
                      );
                    })()}
                  </BentoCard>
                </section>

                <section className="dossier-section" id={`dossier-${dossier.placement.id}-segments`} data-dossier-section="Segmentos y horas" tabIndex={-1}>
                  <PlacementSegments dossier={dossier} onChanged={() => setDetailAttempt((value) => value + 1)} />
                  {showDossierHours && (
                    <BentoCard variant="content" className="dossier-wide" title="Registro de horas" description="Horas reportadas por la persona titular y su estado de revisión por segmento">
                      <HoursReviewList dossier={dossier} onChanged={() => setDetailAttempt((value) => value + 1)} />
                      {dossier.capabilities.record_hours && <div className="section-footer-actions"><button className="btn secondary" type="button" onClick={() => onNavigate("documents")}>Registrar horas</button></div>}
                    </BentoCard>
                  )}
                </section>

                <section className="dossier-section" id={`dossier-${dossier.placement.id}-plan`} data-dossier-section="Plan de trabajo" tabIndex={-1}>
                  <PlacementWorkPlan dossier={dossier} onChanged={() => setDetailAttempt((value) => value + 1)} />
                </section>

                <section className="dossier-section" id={`dossier-${dossier.placement.id}-followup`} data-dossier-section="Seguimiento y evaluaciones" tabIndex={-1}>
                  <PlacementFollowUp dossier={dossier} onChanged={() => setDetailAttempt((value) => value + 1)} />
                </section>

                <section className="dossier-section" id={`dossier-${dossier.placement.id}-documents`} data-dossier-section="Documentos" tabIndex={-1}>
                  <BentoCard variant="content" className="dossier-wide" title="Documentos y versiones" description="Entregas y decisiones guardadas, cuando el rol tiene permiso de lectura">
                    {dossier.documents === null && <p className="muted">Los archivos y el historial de versiones se muestran únicamente a la persona titular y al revisor legal autorizado.</p>}
                    {dossier.documents?.length === 0 && <EmptyState message="No hay requisitos documentales registrados." icon="document" />}
                    {dossier.documents?.map((item) => (
                      <section className="dossier-document" key={item.id}>
                        <div className="dossier-requirement"><strong>{formatDomainLabel(item.kind)}{item.mandatory ? " · obligatorio" : " · opcional"}</strong><Badge>{item.status}</Badge></div>
                        {item.versions?.length ? <ol className="dossier-document-versions">
                          {item.versions.map((version) => (
                            <li key={version.id}>
                              <div><strong>{version.original_filename} · versión {version.revision}</strong>
                                <span>{formatHistoryDate(version.submitted_at)} · entregado por {version.submitted_by}</span>
                                {version.decision && <span><Badge>{version.decision}</Badge>{version.reason ? ` · ${version.reason}` : ""}</span>}
                                {!version.decision && <span className="muted">Sin decisión registrada</span>}
                              </div>
                              <button className="btn secondary small" type="button" onClick={() => void download(item.id, version)}>Descargar</button>
                            </li>
                          ))}
                        </ol> : <p className="muted">No hay versiones de archivo registradas.</p>}
                      </section>
                    ))}
                  </BentoCard>
                </section>

                <section className="dossier-section" id={`dossier-${dossier.placement.id}-messages`} data-dossier-section="Conversación" tabIndex={-1}>
                  <PlacementMessages dossier={dossier} />
                </section>

                <section className="dossier-section dossier-group--split" id={`dossier-${dossier.placement.id}-record`} data-dossier-section="Datos y responsables" tabIndex={-1}>
                  <BentoCard variant="content" title="Oportunidad y postulación" description="Origen y decisiones de selección">
                    <dl className="dossier-facts">
                      <div><dt>Oportunidad</dt><dd>{dossier.opportunity.title}</dd></div>
                      <div><dt>Organización anfitriona</dt><dd>{dossier.opportunity.host_org_name}</dd></div>
                      <div><dt>Programa</dt><dd>{dossier.opportunity.program_name} ({dossier.opportunity.program_code})</dd></div>
                      <div><dt>Estado de la oportunidad</dt><dd><Badge>{dossier.opportunity.state}</Badge></dd></div>
                      <div><dt>Estado de la postulación</dt><dd><Badge>{dossier.application.state}</Badge></dd></div>
                      <div><dt>Resultado de elegibilidad</dt><dd><Badge state={eligibleResult ?? "UNKNOWN"}>{eligibleResult ? formatDomainLabel(eligibleResult) : "No disponible"}</Badge></dd></div>
                      <div><dt>Versión de política aplicada</dt><dd>{dossier.application.eligibility_policy_version === null ? "No registrada" : `v${dossier.application.eligibility_policy_version}`}</dd></div>
                    </dl>
                    <p className="muted">Las decisiones y sus fechas aparecen en la actividad registrada.</p>
                  </BentoCard>

                  <BentoCard variant="content" title="Responsables y supervisión" description="Personas vinculadas al programa o asignadas a esta práctica">
                    <dl className="dossier-facts">
                      <div><dt>Supervisor laboral vigente</dt><dd>{dossier.current_version?.workplace_supervisor_name ?? "Sin asignación registrada"}</dd></div>
                      <div><dt>Supervisión académica</dt><dd>{dossier.responsibles.faculty_supervisors.length ? dossier.responsibles.faculty_supervisors.join(", ") : "Sin asignación registrada"}</dd></div>
                      <div><dt>Coordinación del programa</dt><dd>{dossier.responsibles.program_coordinators.length ? dossier.responsibles.program_coordinators.join(", ") : "Sin asignación registrada"}</dd></div>
                    </dl>
                    <FacultyAssignmentManager dossier={dossier} onChanged={() => setDetailAttempt((value) => value + 1)} />
                  </BentoCard>

                  <BentoCard variant="content" className="dossier-wide" title="Versiones de la práctica" description="Condiciones y supervisión guardadas por versión">
                    {dossier.versions.length === 0 && <EmptyState message="No hay versiones registradas." />}
                    <ol className="dossier-version-list">
                      {dossier.versions.map((version) => (
                        <li className="dossier-version" key={version.version_no}>
                          <div className="row"><strong>Versión {version.version_no}</strong><Badge>{version.status}</Badge></div>
                          <p>{localDate(version.start_date)} – {localDate(version.end_date)} · {version.location}</p>
                          <p><strong>Supervisor laboral:</strong> {version.workplace_supervisor_name ?? "Sin asignación registrada"}</p>
                          <details><summary>Responsabilidades</summary><p className="dossier-preserve-text">{version.responsibilities}</p></details>
                        </li>
                      ))}
                    </ol>
                  </BentoCard>
                </section>

                <section className="dossier-section" id={`dossier-${dossier.placement.id}-activity`} data-dossier-section="Historial" tabIndex={-1}>
                  <BentoCard variant="content" className="dossier-wide" title="Actividad del ciclo de vida" description="Acciones de postulación, selección, aprobación, documentos y práctica que quedaron auditadas, en orden cronológico">
                    <ActivityTimeline events={dossier.activity} />
                  </BentoCard>
                </section>
              </div>
            </div>
          )}
          {!detailLoading && !dossier && !error && selectedRow && <div className="empty dossier-detail-loading"><Spinner /> Preparando el expediente…</div>}
        </div>
      )}
      <span className="sr-only" aria-live="polite">{roles.includes("STUDENT") ? "Vista de estudiante" : "Expedientes según permisos de usuario"}</span>
    </div>
  );
}
