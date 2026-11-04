import { useState, type FormEvent } from "react";
import * as api from "../api";
import type { PlacementDossier } from "../api";
import { Alert, Badge, BentoCard, EmptyState, Spinner, formatDomainLabel } from "./ui";
import { formatHistoryDate } from "../history";

type Props = { dossier: PlacementDossier; onChanged: () => void };

export default function PlacementFollowUp({ dossier, onChanged }: Props) {
  const [progress, setProgress] = useState("");
  const [evaluationKind, setEvaluationKind] = useState<"MIDTERM" | "FINAL">("FINAL");
  const [evaluation, setEvaluation] = useState("");
  const [incidentKind, setIncidentKind] = useState<"INCIDENT" | "CHANGE">("INCIDENT");
  const [summary, setSummary] = useState("");
  const [description, setDescription] = useState("");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const capabilities = dossier.capabilities;
  const showProgress = capabilities.read_progress_reports || capabilities.submit_progress_report;
  const showEvaluations = capabilities.read_evaluations || capabilities.submit_evaluation;
  const showIncidents = capabilities.read_incidents || capabilities.report_incident;
  const showEvidence = capabilities.read_completion_evidence || capabilities.submit_completion_evidence;

  async function save(event: FormEvent, task: () => Promise<unknown>, success: string, reset: () => void) {
    event.preventDefault();
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

  if (!showProgress && !showEvaluations && !showIncidents && !showEvidence) return null;

  return (
    <>
      {(error || notice) && (
        <div className="dossier-wide">
          {error && <Alert kind="error">{error}</Alert>}
          {notice && <Alert kind="success">{notice}</Alert>}
        </div>
      )}

      {showProgress && (
        <BentoCard variant="content" className="dossier-wide" title="Avances de la práctica" description="Actualizaciones narrativas registradas por la persona titular; no representan aprobación académica.">
          {capabilities.read_progress_reports && dossier.progress_reports?.length === 0 && <EmptyState message="Todavía no hay avances registrados." />}
          {capabilities.read_progress_reports && dossier.progress_reports && dossier.progress_reports.length > 0 && (
            <ol className="follow-up-list progress-report-list">
              {dossier.progress_reports.map((record) => (
                <li key={record.revision}>
                  <div className="row"><strong>Actualización {record.revision}</strong><time dateTime={record.created_at}>{formatHistoryDate(record.created_at)}</time></div>
                  <p className="dossier-preserve-text">{record.content}</p>
                  <span className="muted">Registrado por {record.author}</span>
                </li>
              ))}
            </ol>
          )}
          {capabilities.submit_progress_report && (
            <form className="follow-up-form" onSubmit={(event) => void save(
              event, () => api.submitProgressReport(dossier.placement.id, progress),
              "Avance guardado en el expediente.", () => setProgress(""),
            )}>
              <label className="field">Registrar un avance
                <textarea value={progress} maxLength={5000} required rows={4}
                  aria-label="Detalle del avance" placeholder="Describe el trabajo realizado o el progreso observado."
                  onChange={(event) => setProgress(event.currentTarget.value)} />
              </label>
              <button className="btn" type="submit" disabled={busy || !progress.trim()}>{busy ? <Spinner /> : "Guardar avance"}</button>
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
                  <span className="muted">Registrado por {record.evaluator}</span>
                </li>
              ))}
            </ol>
          )}
          {capabilities.submit_evaluation && (
            <form className="follow-up-form evaluation-form" onSubmit={(event) => void save(
              event, () => api.submitPlacementEvaluation(dossier.placement.id, evaluationKind, evaluation),
              "Evaluación guardada en el expediente.", () => setEvaluation(""),
            )}>
              <label className="field">Tipo de evaluación
                <select value={evaluationKind} onChange={(event) => setEvaluationKind(event.currentTarget.value as "MIDTERM" | "FINAL")}>
                  <option value="MIDTERM">Seguimiento intermedio</option>
                  <option value="FINAL">Evaluación final</option>
                </select>
              </label>
              <label className="field">Observaciones
                <textarea value={evaluation} maxLength={8000} required rows={5}
                  aria-label="Observaciones de la evaluación" placeholder="Registra observaciones concretas sobre la experiencia."
                  onChange={(event) => setEvaluation(event.currentTarget.value)} />
              </label>
              <button className="btn" type="submit" disabled={busy || !evaluation.trim()}>{busy ? <Spinner /> : "Guardar evaluación"}</button>
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
                  <span className="muted">{formatHistoryDate(record.reported_at)} · reportado por {record.reporter}</span>
                </li>
              ))}
            </ol>
          )}
          {capabilities.report_incident && (
            <form className="follow-up-form" onSubmit={(event) => void save(
              event, () => api.reportPlacementIncident(dossier.placement.id, incidentKind, summary, description),
              "Registro guardado en el expediente.", () => { setSummary(""); setDescription(""); },
            )}>
              <label className="field">Tipo de registro
                <select value={incidentKind} onChange={(event) => setIncidentKind(event.currentTarget.value as "INCIDENT" | "CHANGE")}>
                  <option value="INCIDENT">Situación o problema</option>
                  <option value="CHANGE">Cambio solicitado o comunicado</option>
                </select>
              </label>
              <label className="field">Resumen
                <input value={summary} maxLength={160} required aria-label="Resumen de situación o cambio"
                  onChange={(event) => setSummary(event.currentTarget.value)} />
              </label>
              <label className="field">Detalle
                <textarea value={description} maxLength={5000} required rows={4} aria-label="Detalle de situación o cambio"
                  onChange={(event) => setDescription(event.currentTarget.value)} />
              </label>
              <button className="btn" type="submit" disabled={busy || !summary.trim() || !description.trim()}>{busy ? <Spinner /> : "Registrar"}</button>
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
                  </div>
                  <button className="btn secondary" type="button" onClick={() => void downloadEvidence(record)}>Descargar</button>
                </li>
              ))}
            </ol>
          )}
          {capabilities.submit_completion_evidence && (
            <form className="follow-up-form" onSubmit={(event) => void save(
              event, () => evidenceFile ? api.submitCompletionEvidence(dossier.placement.id, evidenceFile) : Promise.reject(new Error("Selecciona un archivo.")),
              "Informe final persistido en el expediente.", () => setEvidenceFile(null),
            )}>
              <label className="field">Archivo del informe final
                <input type="file" accept=".pdf,.png,.jpg,.jpeg,.docx" required aria-label="Archivo del informe final"
                  onChange={(event) => setEvidenceFile(event.currentTarget.files?.[0] ?? null)} />
              </label>
              <button className="btn" type="submit" disabled={busy || evidenceFile === null}>{busy ? <Spinner /> : "Entregar informe final"}</button>
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
