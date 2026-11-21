import { useState } from "react";
import * as api from "../api";
import type { PlacementDossier, ProgressHoursEntry } from "../api";
import { Alert, Badge, EmptyState } from "./ui";
import { formatCalendarDate, formatHistoryDate } from "../history";
import { HOURS_REASON_LABELS, HOURS_REVIEW_LABELS, buildHoursReview, formatHours, segmentTone, type HoursReviewDraft } from "../segments";

type Props = { dossier: PlacementDossier; onChanged: () => void };

const EMPTY: HoursReviewDraft = { decision: "ACCEPTED", accepted_hours: "", reason_code: "", reason: "" };

/** CR-05-BR-04: reported hours are listed with their review state; authorized
 * reviewers accept (fully or partially), reject or dispute each entry. */
export default function HoursReviewList({ dossier, onChanged }: Props) {
  const [drafts, setDrafts] = useState<Record<number, HoursReviewDraft>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const entries = dossier.hours ?? [];
  const canReview = Boolean(dossier.capabilities.review_hours) && dossier.placement.state === "ACTIVE";

  async function submit(entry: ProgressHoursEntry) {
    const built = buildHoursReview(drafts[entry.id] ?? EMPTY, entry.hours);
    if ("error" in built) { setError(built.error); return; }
    setBusy(entry.id);
    setError(null);
    setNotice(null);
    try {
      await api.reviewPlacementHours(dossier.placement.id, entry.id, built.value);
      setNotice("Revisión de horas registrada.");
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible registrar la revisión.");
    } finally {
      setBusy(null);
    }
  }

  if (!entries.length) return <EmptyState message="Todavía no hay horas registradas." />;
  return (
    <>
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}
      <ul className="dossier-hours-list">
        {entries.map((entry) => {
          const status = entry.review_status ?? "SUBMITTED";
          const draft = drafts[entry.id] ?? EMPTY;
          const set = (patch: Partial<HoursReviewDraft>) => setDrafts({ ...drafts, [entry.id]: { ...draft, ...patch } });
          return (
            <li key={entry.id} className="hours-entry">
              <span>
                <time dateTime={entry.created_at}>{formatHistoryDate(entry.created_at)}</time>
                {entry.work_date && <small> · jornada {formatCalendarDate(entry.work_date)}</small>}
                {typeof entry.segment_sequence_no === "number" && <small> · segmento {entry.segment_sequence_no}</small>}
                {typeof entry.version_no === "number" && <small> · versión v{entry.version_no}</small>}
                {entry.description && <small> · {entry.description}</small>}
              </span>
              <strong>{formatHours(entry.hours)} h reportadas</strong>
              <span>
                <Badge state={segmentTone(status)} label={HOURS_REVIEW_LABELS[status] ?? status}>{status}</Badge>
                {status === "ACCEPTED" && entry.accepted_hours !== null && entry.accepted_hours !== undefined && <small> · {formatHours(entry.accepted_hours)} h aceptadas</small>}
                {entry.review_reason_code && <small> · {HOURS_REASON_LABELS[entry.review_reason_code]}</small>}
                {entry.review_reason && <small> · {entry.review_reason}</small>}
                {entry.reviewed_by && <small> · {entry.reviewed_by}</small>}
              </span>
              {canReview && status !== "ACCEPTED" && (
                <form className="row segment-inline-form" aria-label={`Revisar horas ${entry.id}`}
                  onSubmit={(event) => { event.preventDefault(); void submit(entry); }}>
                  <label className="sr-only" htmlFor={`decision-${entry.id}`}>Decisión</label>
                  <select id={`decision-${entry.id}`} value={draft.decision} onChange={(event) => set({ decision: event.target.value as HoursReviewDraft["decision"] })}>
                    <option value="ACCEPTED">Aceptar</option>
                    <option value="REJECTED">Rechazar</option>
                    <option value="DISPUTED">Marcar en disputa</option>
                  </select>
                  {draft.decision === "ACCEPTED" && (
                    <>
                      <label className="sr-only" htmlFor={`accepted-${entry.id}`}>Horas aceptadas</label>
                      <input id={`accepted-${entry.id}`} type="number" min="0.1" step="0.1" placeholder={`Todas (${formatHours(entry.hours)})`}
                        value={draft.accepted_hours} onChange={(event) => set({ accepted_hours: event.target.value })} />
                    </>
                  )}
                  <label className="sr-only" htmlFor={`reason-code-${entry.id}`}>Motivo</label>
                  <select id={`reason-code-${entry.id}`} value={draft.reason_code} onChange={(event) => set({ reason_code: event.target.value as HoursReviewDraft["reason_code"] })}>
                    <option value="">Sin código</option>
                    {Object.entries(HOURS_REASON_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                  <label className="sr-only" htmlFor={`reason-${entry.id}`}>Justificación</label>
                  <input id={`reason-${entry.id}`} maxLength={1000} placeholder="Justificación" value={draft.reason} onChange={(event) => set({ reason: event.target.value })} />
                  <button className="btn secondary" type="submit" disabled={busy !== null}>Registrar revisión</button>
                </form>
              )}
            </li>
          );
        })}
      </ul>
    </>
  );
}
