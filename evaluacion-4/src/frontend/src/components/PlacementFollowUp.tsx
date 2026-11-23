import { useState, type FormEvent } from "react";
import * as api from "../api";
import type { PlacementDossier } from "../api";
import { Alert, Badge, BentoCard, EmptyState, Spinner, formatDomainLabel } from "./ui";
import { formatCalendarDate, formatHistoryDate } from "../history";
import { Field, useFieldErrors, type FieldErrors } from "./Field";

type FieldKey = "change" | "progress" | "evaluation" | "summary" | "description" | "evidence";

type Props = { dossier: PlacementDossier; onChanged: () => void };

export default function PlacementFollowUp({ dossier, onChanged }: Props) {
  const [progress, setProgress] = useState("");
  const [evaluationKind, setEvaluationKind] = useState<"MIDTERM" | "FINAL">("FINAL");
  const [evaluation, setEvaluation] = useState("");
  const [incidentKind, setIncidentKind] = useState<"INCIDENT" | "CHANGE">("INCIDENT");
  const [summary, setSummary] = useState("");
  const [description, setDescription] = useState("");
  const [changeLocation, setChangeLocation] = useState("");
  const [changeResponsibilities, setChangeResponsibilities] = useState("");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const capabilities = dossier.capabilities;
  const fid = `follow-up-${dossier.placement.id}`;
  const fieldId = (key: FieldKey) => `${fid}-${key}`;
  const fields = useFieldErrors<FieldKey>(fieldId);
  const showProgress = capabilities.read_progress_reports || capabilities.submit_progress_report;
  const showEvaluations = capabilities.read_evaluations || capabilities.submit_evaluation;
  const showIncidents = capabilities.read_incidents || capabilities.report_incident;
  const showEvidence = capabilities.read_completion_evidence || capabilities.submit_completion_evidence;
  const showChanges = dossier.versions.length > 0 || capabilities.propose_change || capabilities.approve_change;

  // `invalid` holds the same rules the form enforced before; on failure the
  // first invalid field receives focus and its error is announced.
  async function save(event: FormEvent, invalid: FieldErrors<FieldKey>, task: () => Promise<unknown>, success: string, reset: () => void) {
    event.preventDefault();
    if (!fields.report(invalid)) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await task();
      reset();
      setNotice(success);
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible guardar el registro.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadEvidence(evidence: NonNullable<PlacementDossier["completion_evidence"]>[number]) {
    setError(null);
    try {
      await api.downloadCompletionEvidence(dossier.placement.id, evidence);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible descargar la evidencia.");
    }
  }

  async function approveChange(versionId: number) {
    const version = dossier.versions.find((candidate) => candidate.id === versionId);
    if (!version) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.approvePlacementChange(dossier.placement.id, versionId);
      setNotice("Versión aprobada y convertida en la versión vigente.");
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible aprobar la versión.");
    } finally {
      setBusy(false);
    }
  }

  if (!showProgress && !showEvaluations && !showIncidents && !showEvidence && !showChanges) return null;

  return (
    <>
      {(error || notice) && (
        <div className="dossier-wide">
          {error && <Alert kind="error">{error}</Alert>}
          {notice && <Alert kind="success">{notice}</Alert>}
        </div>
      )}

      {showChanges && <BentoCard variant="content" className="dossier-wide" title="Cambios de la práctica" description="Las propuestas crean una versión inmutable y quedan pendientes de la autoridad institucional configurada.">
        {dossier.versions.length > 0 && (
          <ol className="follow-up-list" aria-label="Versiones de la práctica">
            {dossier.versions.map((version) => (
              <li key={version.version_no}>
                <div className="row"><strong>Versión {version.version_no}</strong><Badge state={version.status}>{formatDomainLabel(version.status)}</Badge></div>
                <p>{version.location} · {formatCalendarDate(version.start_date)} – {formatCalendarDate(version.end_date)}</p>
                <span className="muted">Supervisor laboral: {version.workplace_supervisor_name ?? "Sin asignación"}</span>
                {version.status === "PROPOSED" && capabilities.approve_change && (
                  <button className="btn secondary" type="button" disabled={busy} onClick={() => void approveChange(version.id)}>
                    Aprobar versión
                  </button>
                )}
              </li>
            ))}
          </ol>
        )}
        {capabilities.propose_change && (
          <form className="follow-up-form" noValidate onSubmit={(event) => void save(
            event,
            changeLocation.trim() || changeResponsibilities.trim() ? {} : { change: "Indica una nueva ubicación o responsabilidades actualizadas." },
            () => api.proposePlacementChange(dossier.placement.id, {
              ...(changeLocation.trim() ? { location: changeLocation.trim() } : {}),
              ...(changeResponsibilities.trim() ? { responsibilities: changeResponsibilities.trim() } : {}),
            }),
            "Cambio propuesto y guardado como nueva versión.",
            () => { setChangeLocation(""); setChangeResponsibilities(""); },
          )}>
            <Field id={fieldId("change")} label="Nueva ubicación de la práctica (opcional)"
              hint="Completa al menos uno de los dos campos." error={fields.errors.change}>
              <input value={changeLocation} maxLength={240}
                onChange={(event) => { setChangeLocation(event.currentTarget.value); fields.clear("change"); }} />
            </Field>
            <Field id={`${fid}-responsibilities`} label="Responsabilidades actualizadas de la práctica (opcional)">
              <textarea value={changeResponsibilities} maxLength={5000} rows={4}
                onChange={(event) => { setChangeResponsibilities(event.currentTarget.value); fields.clear("change"); }} />
            </Field>
            <button className="btn" type="submit" disabled={busy}>
              {busy ? <Spinner /> : "Proponer cambio"}
            </button>
          </form>
        )}
      </BentoCard>}

      {showProgress && (
        <BentoCard variant="content" className="dossier-wide" title="Avances de la práctica" description="Actualizaciones narrativas registradas por la persona titular; no representan aprobación académica.">
          {capabilities.read_progress_reports && dossier.progress_reports?.length === 0 && <EmptyState message="Todavía no hay avances registrados." />}
          {capabilities.read_progress_reports && dossier.progress_reports && dossier.progress_reports.length > 0 && (
            <ol className="follow-up-list progress-report-list">
              {dossier.progress_reports.map((record) => (
                <li key={record.revision}>
                  <div className="row"><strong>Actualización {record.revision}</strong><time dateTime={record.created_at}>{formatHistoryDate(record.created_at)}</time></div>
                  <p className="dossier-preserve-text">{record.content}</p>
                  {typeof record.version_no === "number" && <span className="muted">Versión vigente al registrar: v{record.version_no}</span>}
                  <span className="muted">Registrado por {record.author}</span>
                </li>
              ))}
            </ol>
          )}
          {capabilities.submit_progress_report && (
            <form className="follow-up-form" noValidate onSubmit={(event) => void save(
              event, progress.trim() ? {} : { progress: "Describe el avance antes de guardarlo." },
              () => api.submitProgressReport(dossier.placement.id, progress),
              "Avance guardado en el expediente.", () => setProgress(""),
            )}>
              <Field id={fieldId("progress")} label="Detalle del avance" error={fields.errors.progress}>
                <textarea value={progress} maxLength={5000} required rows={4}
                  placeholder="Describe el trabajo realizado o el progreso observado…"
                  onChange={(event) => { setProgress(event.currentTarget.value); fields.clear("progress"); }} />
              </Field>
              <button className="btn" type="submit" disabled={busy}>{busy ? <Spinner /> : "Guardar avance"}</button>
            </form>
          )}
        </BentoCard>
      )}

      {showEvaluations && (
        <BentoCard variant="content" className="dossier-wide" title="Evaluaciones narrativas" description="Observaciones persistidas por la supervisión laboral, sin calificación, escala ni ponderación configurada.">
          {capabilities.read_evaluations && dossier.evaluations?.length === 0 && <EmptyState message="Todavía no hay evaluaciones registradas." />}
          {capabilities.read_evaluations && dossier.evaluations && dossier.evaluations.length > 0 && (
            <ol className="follow-up-list">
              {dossier.evaluations.map((record) => (
                <li key={`${record.kind}-${record.revision}`}>
                  <div className="row"><strong>{formatDomainLabel(record.kind)} · versión {record.revision}</strong><time dateTime={record.submitted_at}>{formatHistoryDate(record.submitted_at)}</time></div>
                  <p className="dossier-preserve-text">{record.narrative}</p>
                  {typeof record.version_no === "number" && <span className="muted">Versión vigente al registrar: v{record.version_no}</span>}
                  <span className="muted">Registrado por {record.evaluator}</span>
                </li>
              ))}
            </ol>
          )}
          {capabilities.submit_evaluation && (
            <form className="follow-up-form evaluation-form" noValidate onSubmit={(event) => void save(
              event, evaluation.trim() ? {} : { evaluation: "Registra las observaciones de la evaluación." },
              () => api.submitPlacementEvaluation(dossier.placement.id, evaluationKind, evaluation),
              "Evaluación guardada en el expediente.", () => setEvaluation(""),
            )}>
              <Field id={`${fid}-evaluation-kind`} label="Tipo de evaluación">
                <select value={evaluationKind} onChange={(event) => setEvaluationKind(event.currentTarget.value as "MIDTERM" | "FINAL")}>
                  <option value="MIDTERM">Seguimiento intermedio</option>
                  <option value="FINAL">Evaluación final</option>
                </select>
              </Field>
              <Field id={fieldId("evaluation")} label="Observaciones de la evaluación" error={fields.errors.evaluation}>
                <textarea value={evaluation} maxLength={8000} required rows={5}
                  placeholder="Registra observaciones concretas sobre la experiencia…"
                  onChange={(event) => { setEvaluation(event.currentTarget.value); fields.clear("evaluation"); }} />
              </Field>
              <button className="btn" type="submit" disabled={busy}>{busy ? <Spinner /> : "Guardar evaluación"}</button>
            </form>
          )}
        </BentoCard>
      )}

      {showIncidents && (
        <BentoCard variant="content" className="dossier-wide" title="Situaciones y cambios reportados" description="Cada entrada conserva su estado de reporte. No representa revisión o resolución y no aprueba una nueva versión de la práctica.">
          {capabilities.read_incidents && dossier.incidents?.length === 0 && <EmptyState message="No hay situaciones o cambios reportados." />}
          {capabilities.read_incidents && dossier.incidents && dossier.incidents.length > 0 && (
            <ol className="follow-up-list">
              {dossier.incidents.map((record) => (
                <li key={record.revision}>
                  <div className="row"><strong>{record.summary}</strong><div className="row"><Badge>{record.kind}</Badge><Badge state={record.status}>{record.status}</Badge></div></div>
                  <p className="dossier-preserve-text">{record.description}</p>
                  {typeof record.version_no === "number" && <span className="muted">Versión vigente al reportar: v{record.version_no}</span>}
                  <span className="muted">{formatHistoryDate(record.reported_at)} · reportado por {record.reporter}</span>
                </li>
              ))}
            </ol>
          )}
          {capabilities.report_incident && (
            <form className="follow-up-form" noValidate onSubmit={(event) => void save(
              event,
              {
                ...(summary.trim() ? {} : { summary: "Escribe un resumen breve." }),
                ...(description.trim() ? {} : { description: "Describe la situación o el cambio." }),
              },
              () => api.reportPlacementIncident(dossier.placement.id, incidentKind, summary, description),
              "Registro guardado en el expediente.", () => { setSummary(""); setDescription(""); },
            )}>
              <Field id={`${fid}-incident-kind`} label="Tipo de registro">
                <select value={incidentKind} onChange={(event) => setIncidentKind(event.currentTarget.value as "INCIDENT" | "CHANGE")}>
                  <option value="INCIDENT">Situación o problema</option>
                  <option value="CHANGE">Cambio solicitado o comunicado</option>
                </select>
              </Field>
              <Field id={fieldId("summary")} label="Resumen de situación o cambio" error={fields.errors.summary}>
                <input value={summary} maxLength={160} required
                  onChange={(event) => { setSummary(event.currentTarget.value); fields.clear("summary"); }} />
              </Field>
              <Field id={fieldId("description")} label="Detalle de situación o cambio" error={fields.errors.description}>
                <textarea value={description} maxLength={5000} required rows={4}
                  onChange={(event) => { setDescription(event.currentTarget.value); fields.clear("description"); }} />
              </Field>
              <button className="btn" type="submit" disabled={busy}>{busy ? <Spinner /> : "Registrar"}</button>
            </form>
          )}
        </BentoCard>
      )}

      {showEvidence && (
        <BentoCard variant="content" className="dossier-wide" title="Evidencia final" description="El informe se almacena con versiones. Su recepción no equivale a una evaluación ni a una aprobación institucional.">
          {capabilities.read_completion_evidence && dossier.completion_evidence?.length === 0 && <EmptyState message="Todavía no hay informe final persistido." />}
          {capabilities.read_completion_evidence && dossier.completion_evidence && dossier.completion_evidence.length > 0 && (
            <ol className="dossier-document-versions">
              {dossier.completion_evidence.map((record) => (
                <li key={`${record.kind}-${record.revision}`}>
                  <div>
                    <strong>{record.original_filename} · versión {record.revision}</strong>
                    <span>{formatHistoryDate(record.submitted_at)} · entregado por {record.submitted_by}</span>
                    {typeof record.version_no === "number" && <span>Versión vigente al entregar: v{record.version_no}</span>}
                  </div>
                  <button className="btn secondary" type="button" onClick={() => void downloadEvidence(record)}>Descargar</button>
                </li>
              ))}
            </ol>
          )}
          {capabilities.submit_completion_evidence && (
            <form className="follow-up-form" noValidate onSubmit={(event) => void save(
              event, evidenceFile ? {} : { evidence: "Selecciona el archivo del informe final." },
              () => evidenceFile ? api.submitCompletionEvidence(dossier.placement.id, evidenceFile) : Promise.reject(new Error("Selecciona un archivo.")),
              "Informe final persistido en el expediente.", () => setEvidenceFile(null),
            )}>
              <Field id={fieldId("evidence")} label="Archivo del informe final" hint="PDF, PNG, JPG o DOCX." error={fields.errors.evidence}>
                <input type="file" accept=".pdf,.png,.jpg,.jpeg,.docx" required
                  onChange={(event) => { setEvidenceFile(event.currentTarget.files?.[0] ?? null); fields.clear("evidence"); }} />
              </Field>
              <button className="btn" type="submit" disabled={busy}>{busy ? <Spinner /> : "Entregar informe final"}</button>
            </form>
          )}
          {!capabilities.submit_completion_evidence && capabilities.read_completion_evidence &&
            dossier.completion_requirements?.some((requirement) => requirement.kind === "FINAL_REPORT" && !requirement.satisfied) &&
            <p className="dossier-gate-note">El informe final sigue pendiente; la entrega corresponde a la persona titular.</p>}
        </BentoCard>
      )}
    </>
  );
}
