import { useState } from "react";
import * as api from "../../api";
import type { PlacementDossier, PlacementSegment } from "../../api";
import { Badge, Spinner, formatDomainLabel } from "../ui";
import { DisabledReason } from "../overlays";
import { formatCalendarDate, formatHistoryDate } from "../../history";
import {
  MODALITY_LABELS,
  RECOGNITION_LABELS,
  SEGMENT_ORIGIN_LABELS,
  SEGMENT_STATUS_LABELS,
  formatHours,
  segmentTone,
} from "../../segments";

export type SegmentPanelKind = "terminate" | "transfer" | "cancel";

type Props = {
  pid: number;
  segment: PlacementSegment;
  dossier: PlacementDossier;
  busy: string | null;
  run: (key: string, action: () => Promise<unknown>, success: string) => Promise<boolean>;
  onOpenPanel: (segmentId: number, kind: SegmentPanelKind) => void;
  onError: (message: string) => void;
};

function localDate(value: string | null | undefined): string {
  return formatCalendarDate(value, "—");
}

/** One segment of the timeline: facts, conditions, history and the actions allowed for the current role. */
export function SegmentItem({ pid, segment, dossier, busy, run, onOpenPanel, onError }: Props) {
  const caps = dossier.capabilities;
  const isActive = dossier.placement.state === "ACTIVE";
  const [references, setReferences] = useState<Record<number, string>>({});
  const pendingConditions = segment.conditions.filter((condition) => condition.status !== "SATISFIED");
  const segmentHours = (dossier.hours_summary?.segments ?? []).find((row) => row.segment_id === segment.id);
  const activateReasonId = `segment-${segment.id}-activate-reason`;
  return (
    <li className={`segment-item segment-${segment.status.toLowerCase()}`}>
      <span className="segment-marker" aria-hidden="true">{segment.sequence_no}</span>
      <div className="segment-body">
        <div className="row segment-heading">
          <h3 className="segment-title">Segmento {segment.sequence_no} · {segment.host_org_name}{segment.unit ? ` · ${segment.unit}` : ""}</h3>
          <Badge state={segmentTone(segment.status)} label={SEGMENT_STATUS_LABELS[segment.status]}>{segment.status}</Badge>
        </div>
        <dl className="segment-facts">
          <div><dt>Periodo</dt><dd>{localDate(segment.start_date)} – {localDate(segment.end_date)}</dd></div>
          <div><dt>Supervisor laboral</dt><dd>{segment.workplace_supervisor_name ?? "Sin asignación registrada"}</dd></div>
          <div><dt>Modalidad</dt><dd>{segment.modality ? MODALITY_LABELS[segment.modality] : "No registrada"}</dd></div>
          <div><dt>Horas</dt><dd>
            {segmentHours
              ? <>{formatHours(segmentHours.accepted)} h aceptadas · {formatHours(segmentHours.reported)} h reportadas</>
              : "Sin registros visibles"}
            {segment.expected_hours !== null && <span className="segment-fact-note">Esperadas: {formatHours(segment.expected_hours)} h</span>}
          </dd></div>
          <div><dt>Origen</dt><dd>{SEGMENT_ORIGIN_LABELS[segment.origin] ?? segment.origin}</dd></div>
          {segment.ended_on && <div><dt>Cierre efectivo</dt><dd>{localDate(segment.ended_on)}</dd></div>}
          {segment.work_recognition && <div><dt>Trabajo previo</dt><dd>{RECOGNITION_LABELS[segment.work_recognition]}</dd></div>}
        </dl>
        {segment.end_reason_shared && <p className="segment-reason"><strong>Motivo:</strong> {segment.end_reason_shared}</p>}
        {segment.end_reason_internal && <p className="segment-internal"><strong>Motivo confidencial (solo roles autorizados):</strong> {segment.end_reason_internal}</p>}
        {segment.recognition_note && <p className="muted">Nota de reconocimiento: {segment.recognition_note}</p>}
        <details className="segment-details">
          <summary>Responsabilidades, condiciones e historial{pendingConditions.length ? ` · ${pendingConditions.length} condición(es) pendiente(s)` : ""}</summary>
          <div className="segment-details-body">
            <p className="dossier-preserve-text">{segment.responsibilities}</p>
            <h4>Condiciones de habilitación</h4>
            {segment.conditions.length === 0 && <p className="muted">Sin condiciones de habilitación registradas.</p>}
            {segment.conditions.length > 0 && <ul className="requirement-list">
              {segment.conditions.map((condition) => (
                <li className="dossier-requirement" key={condition.id}>
                  <span>{formatDomainLabel(condition.kind)}{condition.reference ? ` · ${condition.reference}` : ""}{condition.confirmed_by ? ` · ${condition.confirmed_by}` : ""}</span>
                  <Badge state={segmentTone(condition.status)} label={condition.status === "SATISFIED" ? "Cumplida" : "Pendiente"}>{condition.status}</Badge>
                  {caps.confirm_segment_conditions && isActive && segment.status === "PLANNED" && condition.status === "REQUIRED" && (
                    <form className="row segment-inline-form" onSubmit={(event) => {
                      event.preventDefault();
                      const reference = (references[condition.id] ?? "").trim();
                      if (!reference) { onError("Indica la referencia del documento verificado."); return; }
                      void run(`cond-${condition.id}`, () => api.confirmSegmentCondition(pid, segment.id, condition.id, reference), "Condición confirmada.");
                    }}>
                      <label className="sr-only" htmlFor={`cond-${condition.id}`}>Referencia verificada</label>
                      <input id={`cond-${condition.id}`} placeholder="Referencia verificada…" maxLength={500} required
                        value={references[condition.id] ?? ""} onChange={(event) => setReferences({ ...references, [condition.id]: event.target.value })} />
                      <button className="btn secondary small" type="submit" disabled={busy !== null}>Confirmar condición</button>
                    </form>
                  )}
                </li>
              ))}
            </ul>}
            {segment.status_history.length > 0 && <>
              <h4>Historial del segmento</h4>
              <ol className="segment-history" aria-label={`Historial del segmento ${segment.sequence_no}`}>
                {segment.status_history.map((entry, index) => (
                  <li key={index}>
                    <time>{formatHistoryDate(entry.changed_at)}</time>
                    <span>{entry.from_status ? SEGMENT_STATUS_LABELS[entry.from_status] : "Inicio"} → {SEGMENT_STATUS_LABELS[entry.to_status]}{entry.actor_name ? ` · ${entry.actor_name}` : ""}</span>
                  </li>
                ))}
              </ol>
            </>}
          </div>
        </details>

        {caps.manage_segments && isActive && segment.status === "PLANNED" && (
          <div className="segment-actions">
            <button className="btn small" type="button" disabled={busy !== null || pendingConditions.length > 0}
              aria-describedby={pendingConditions.length ? activateReasonId : undefined}
              onClick={() => void run(`activate-${segment.id}`, () => api.activatePlacementSegment(pid, segment.id), "Segmento activado.")}>
              {busy === `activate-${segment.id}` ? <Spinner /> : "Activar segmento"}
            </button>
            <button className="btn secondary small" type="button" onClick={() => onOpenPanel(segment.id, "cancel")}>Cancelar segmento</button>
            {pendingConditions.length > 0 && (
              <DisabledReason id={activateReasonId}>
                Para activar falta confirmar: {pendingConditions.map((c) => formatDomainLabel(c.kind)).join(", ")}.
              </DisabledReason>
            )}
          </div>
        )}
        {caps.manage_segments && isActive && segment.status === "ACTIVE" && (
          <div className="segment-actions">
            <button className="btn secondary small" type="button" disabled={busy !== null}
              onClick={() => void run(`complete-${segment.id}`, () => api.completePlacementSegment(pid, segment.id), "Segmento completado. El siguiente no se activa automáticamente.")}>
              {busy === `complete-${segment.id}` ? <Spinner /> : "Completar segmento"}
            </button>
            <button className="btn secondary small" type="button" onClick={() => onOpenPanel(segment.id, "transfer")}>Transferir</button>
            <button className="btn secondary small" type="button" onClick={() => onOpenPanel(segment.id, "terminate")}>Terminar anticipadamente</button>
          </div>
        )}
      </div>
    </li>
  );
}
