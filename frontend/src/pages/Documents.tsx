import { useEffect, useState, type FormEvent } from "react";
import * as api from "../api";
import type { ActivationStatus, Application, ChecklistItem, DocumentSubmission } from "../api";
import { Alert, Badge, EmptyState, Icon, PageHeader, Skeleton, Spinner, formatDomainLabel } from "../components/ui";
import { Field } from "../components/Field";
import PlacementHistory from "../components/PlacementHistory";
import { hoursFromHistory, totalHours, type HoursEntry } from "../progress";
import { HOURS_REVIEW_LABELS } from "../segments";
import { formatHistoryDate } from "../history";
import { errorMessage, useAsyncAction } from "../useAsyncAction";

const ACCEPTED_FILES = ".pdf,.png,.jpg,.jpeg,.docx,application/pdf,image/png,image/jpeg,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

function isTracked(application: Application) {
  return Boolean(application.placement_id) &&
    (application.placement_state === "DOCUMENTATION_PENDING" || application.placement_state === "ACTIVE");
}

function requirementCounts(items: ChecklistItem[]) {
  const documents = items.filter((item) => item.kind.startsWith("DOC_"));
  return {
    total: documents.length,
    approved: documents.filter((item) => item.status === "APPROVED").length,
    submitted: documents.filter((item) => item.status === "SUBMITTED").length,
    rejected: documents.filter((item) => item.status === "REJECTED").length,
    pending: documents.filter((item) => item.status === "REQUIRED").length,
  };
}

export default function Documents() {
  const [apps, setApps] = useState<Application[] | null>(null);
  const [statuses, setStatuses] = useState<Record<number, ActivationStatus>>({});
  const [submissions, setSubmissions] = useState<Record<string, DocumentSubmission[]>>({});
  const [hours, setHours] = useState<Record<number, HoursEntry[]>>({});
  const [hoursDraft, setHoursDraft] = useState<Record<number, string>>({});
  const [workDateDraft, setWorkDateDraft] = useState<Record<number, string>>({});
  const [descriptionDraft, setDescriptionDraft] = useState<Record<number, string>>({});
  const [hoursErrors, setHoursErrors] = useState<Record<number, string>>({});
  const [files, setFiles] = useState<Record<number, File>>({});
  const { busy, error, notice, run, setError, setNotice } = useAsyncAction();

  async function reload() {
    try {
      const list = await api.listApplications();
      const placements = list.filter(isTracked);
      const statusPairs = await Promise.all(placements.map(async (a) => {
        const pid = a.placement_id!;
        return [pid, await api.activationStatus(pid)] as const;
      }));
      const statusMap = Object.fromEntries(statusPairs);
      const submissionPairs = await Promise.all(placements.flatMap((a) => {
        const pid = a.placement_id!;
        return statusMap[pid].items.map(async (item) => [
          `${pid}:${item.id}`,
          await api.listDocumentSubmissions(pid, item.id),
        ] as const);
      }));
      const hoursPairs = await Promise.all(placements
        .filter((a) => a.placement_state === "ACTIVE")
        .map(async (a) => [a.placement_id!, hoursFromHistory(await api.listPlacementHours(a.placement_id!))] as const));
      setApps(list);
      setStatuses(statusMap);
      setSubmissions(Object.fromEntries(submissionPairs));
      setHours(Object.fromEntries(hoursPairs));
    } catch (err) {
      setError(errorMessage(err, "No fue posible cargar tus documentos."));
    }
  }

  useEffect(() => { void reload(); }, []);

  async function submitAndAnnounce(pid: number, itemId: number) {
    const file = files[itemId];
    if (!file) return;
    let revision: number | null = null;
    const ok = await run(`doc-${itemId}`, async () => {
      const result = await api.submitDocument(pid, itemId, file);
      revision = result.revision;
      setFiles((current) => {
        const next = { ...current };
        delete next[itemId];
        return next;
      });
      await reload();
    });
    if (ok && revision !== null) setNotice(`Documento enviado como versión ${revision}.`);
  }

  async function download(pid: number, itemId: number, submission: DocumentSubmission) {
    await run(`download-${submission.id}`, () => api.downloadDocument(pid, itemId, submission));
  }

  async function recordHours(pid: number, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = Number(hoursDraft[pid]);
    if (!Number.isFinite(value) || value <= 0) {
      setHoursErrors((current) => ({ ...current, [pid]: "Ingresa una cantidad de horas mayor que cero." }));
      document.getElementById(`hours-${pid}`)?.focus();
      return;
    }
    setHoursErrors((current) => ({ ...current, [pid]: "" }));
    const ok = await run(`hours-${pid}`, async () => {
      await api.recordPlacementHours(pid, value, {
        work_date: workDateDraft[pid] || undefined,
        description: descriptionDraft[pid] || undefined,
      });
      await reload();
    }, "Las horas quedaron registradas en el segmento activo y quedan pendientes de revisión.");
    if (ok) {
      setHoursDraft((current) => ({ ...current, [pid]: "" }));
      setWorkDateDraft((current) => ({ ...current, [pid]: "" }));
      setDescriptionDraft((current) => ({ ...current, [pid]: "" }));
    }
  }

  const placements = (apps ?? []).filter(isTracked);

  return (
    <div className="page-stack">
      <PageHeader eyebrow="Mi práctica" title="Mis documentos" description="Consulta los requisitos, entrega archivos y revisa las decisiones del equipo académico." />
      <Alert kind="info">Carga únicamente archivos sintéticos para esta demostración. Se aceptan PDF, PNG, JPG y DOCX de hasta 10 MB.</Alert>
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}
      {apps === null && !error && <Skeleton lines={5} />}
      {apps !== null && placements.length === 0 && (
        <EmptyState icon="document" message="No tienes prácticas con requisitos documentales pendientes o en seguimiento." />
      )}
      {placements.map((a) => {
        const pid = a.placement_id!;
        const status = statuses[pid];
        const counts = requirementCounts(status?.items ?? []);
        const active = a.placement_state === "ACTIVE";
        const entries = hours[pid] ?? [];
        return (
          <section className="data-panel document-placement" key={a.id} aria-labelledby={`placement-${pid}-title`}>
            <div className="data-panel-header">
              <div>
                <h2 id={`placement-${pid}-title`}>{a.title}</h2>
                <p className="data-panel-meta">{active ? "Práctica activa: registra horas y mantén vigentes tus documentos." : "Documentación para activar la práctica."}</p>
              </div>
              <Badge>{a.placement_state}</Badge>
            </div>

            {status && counts.total > 0 && (
              <dl className="state-summary document-summary" aria-label={`Resumen de requisitos de ${a.title}`}>
                <div><dt>Aprobados</dt><dd><strong>{counts.approved}</strong> de {counts.total}</dd></div>
                <div><dt>En revisión</dt><dd><strong>{counts.submitted}</strong></dd></div>
                <div><dt>Por entregar</dt><dd><strong>{counts.pending}</strong></dd></div>
                <div><dt>Con corrección</dt><dd><strong>{counts.rejected}</strong></dd></div>
              </dl>
            )}
            {status && a.placement_state === "DOCUMENTATION_PENDING" && (
              <p className={`readiness-note${status.ready_to_activate ? " is-ready" : ""}`}>
                <Icon name={status.ready_to_activate ? "status-success" : "status-warning"} />
                <span>
                  {status.ready_to_activate
                    ? "Los requisitos están aprobados; el coordinador puede activar la práctica."
                    : `Pendiente para activar: ${status.unmet.map(formatDomainLabel).join(", ") || "—"}`}
                </span>
              </p>
            )}
            {status?.activation_noncompliant && (
              <Alert kind="info">La práctica sigue activa. Corrige los requisitos rechazados para completar el ciclo.</Alert>
            )}

            {active && (
              <section className="work-log-card" aria-label={`Seguimiento de horas de ${a.title}`}>
                <div className="work-log-heading">
                  <div>
                    <h3>Horas de práctica</h3>
                    <p className="muted">Se registran en el segmento activo. Solo cuentan para el cierre cuando el rol revisor configurado las acepta.</p>
                  </div>
                  <div className="work-log-total">
                    <span className="muted">Reportadas</span>
                    <strong className="metric-value">{totalHours(entries)} h</strong>
                  </div>
                </div>
                <form className="work-log-form" noValidate onSubmit={(event) => void recordHours(pid, event)}>
                  <Field id={`hours-${pid}`} label="Horas realizadas" error={hoursErrors[pid] || null}>
                    <input type="number" min="0.1" step="0.1" inputMode="decimal" required value={hoursDraft[pid] ?? ""}
                      onChange={(event) => {
                        const next = event.target.value;
                        setHoursDraft((current) => ({ ...current, [pid]: next }));
                        setHoursErrors((current) => ({ ...current, [pid]: "" }));
                      }} />
                  </Field>
                  <Field id={`work-date-${pid}`} label="Fecha de la jornada (opcional)">
                    <input type="date" value={workDateDraft[pid] ?? ""}
                      onChange={(event) => { const next = event.target.value; setWorkDateDraft((current) => ({ ...current, [pid]: next })); }} />
                  </Field>
                  <Field id={`hours-description-${pid}`} label="Descripción (opcional)" className="work-log-description">
                    <input maxLength={1000} value={descriptionDraft[pid] ?? ""}
                      onChange={(event) => { const next = event.target.value; setDescriptionDraft((current) => ({ ...current, [pid]: next })); }} />
                  </Field>
                  <button className="btn" type="submit" disabled={busy === `hours-${pid}` || !hoursDraft[pid]}>
                    {busy === `hours-${pid}` ? <Spinner /> : "Registrar horas"}
                  </button>
                </form>
                {entries.length > 0 ? (
                  <ul className="work-log-list" aria-label="Registros de horas">
                    {entries.map((entry) => (
                      <li key={entry.id}>
                        <span>
                          {formatHistoryDate(entry.occurredAt)}
                          {entry.segmentNo ? ` · segmento ${entry.segmentNo}` : ""}
                          {entry.reviewStatus ? ` · ${HOURS_REVIEW_LABELS[entry.reviewStatus] ?? entry.reviewStatus}` : ""}
                        </span>
                        <strong>{entry.hours} h</strong>
                      </li>
                    ))}
                  </ul>
                ) : <p className="muted">Todavía no hay horas registradas.</p>}
              </section>
            )}

            {status && status.items.length > 0 && (
              <div className="document-requirements">
                <h3>Requisitos documentales</h3>
                <div className="table-scroll" tabIndex={0} aria-label={`Requisitos documentales de ${a.title}`}>
                  <table className="data-table data-table--stack">
                    <thead><tr><th scope="col">Requisito</th><th scope="col">Estado</th><th scope="col">Entrega actual</th><th scope="col">Revisión</th><th scope="col" className="col-actions">Acción</th></tr></thead>
                    <tbody>
                      {status.items.map((item) => {
                        const latest = (submissions[`${pid}:${item.id}`] ?? [])[0];
                        const label = formatDomainLabel(item.kind);
                        const canUpload = item.kind.startsWith("DOC_") && (item.status === "REQUIRED" || item.status === "REJECTED");
                        const chosen = files[item.id];
                        return (
                          <tr key={item.id} className={item.status === "REJECTED" ? "needs-attention" : undefined}>
                            <td data-label="Requisito">
                              <span className="cell-primary">{label}</span>
                              <span className="cell-secondary">{item.mandatory ? "Obligatorio" : "Opcional"}</span>
                            </td>
                            <td data-label="Estado"><Badge>{item.status}</Badge></td>
                            <td data-label="Entrega actual">
                              {latest ? (
                                <>
                                  <span className="cell-primary file-name">{latest.original_filename}</span>
                                  <span className="cell-secondary">Versión {latest.revision}</span>
                                  <button className="btn link" type="button" disabled={busy === `download-${latest.id}`}
                                    onClick={() => void download(pid, item.id, latest)}>Descargar</button>
                                </>
                              ) : <span className="muted">Sin archivo</span>}
                            </td>
                            <td data-label="Revisión">
                              {latest?.decision
                                ? <><Badge>{latest.decision}</Badge>{latest.reason && <span className="cell-secondary review-reason">{latest.reason}</span>}</>
                                : <span className="muted">{item.status === "SUBMITTED" ? "En revisión" : "—"}</span>}
                            </td>
                            <td className="col-actions" data-label={canUpload ? "Entrega" : undefined}>
                              {canUpload && (
                                <div className="file-upload">
                                  <label className="file-picker">
                                    <input
                                      className="sr-only"
                                      aria-label={`Archivo para ${label}`}
                                      type="file"
                                      accept={ACCEPTED_FILES}
                                      onChange={(event) => {
                                        const selected = event.currentTarget.files?.[0];
                                        if (selected) setFiles((current) => ({ ...current, [item.id]: selected }));
                                      }}
                                    />
                                    <span className="btn secondary small" aria-hidden="true">Elegir archivo</span>
                                    <span className="file-picker-name">{chosen ? chosen.name : "Ningún archivo"}</span>
                                  </label>
                                  <button className="btn small" type="button" disabled={!chosen || busy === `doc-${item.id}`}
                                    onClick={() => void submitAndAnnounce(pid, item.id)}>
                                    {busy === `doc-${item.id}` ? <Spinner /> : item.status === "REJECTED" ? "Reenviar" : "Enviar"}
                                  </button>
                                </div>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            <PlacementHistory placementId={pid} />
          </section>
        );
      })}
    </div>
  );
}
