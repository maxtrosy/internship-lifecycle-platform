import { useState, type FormEvent, type ReactNode } from "react";
import * as api from "../api";
import type { PlacementDossier, PlacementSegment, SegmentOption, WorkRecognition } from "../api";
import { Alert, Badge, BentoCard, EmptyState, Spinner, formatDomainLabel } from "./ui";
import { formatHistoryDate } from "../history";
import {
  EMPTY_SEGMENT_DRAFT,
  MODALITY_LABELS,
  RECOGNITION_LABELS,
  SEGMENT_ORIGIN_LABELS,
  SEGMENT_STATUS_LABELS,
  buildSegmentInput,
  formatHours,
  hoursOverview,
  segmentGateBlockers,
  segmentTone,
  todayIso,
  type SegmentDraft,
} from "../segments";

type Props = { dossier: PlacementDossier; onChanged: () => void };
type Panel = { segmentId: number; kind: "terminate" | "transfer" | "cancel" } | null;

function localDate(value: string | null | undefined): string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}/.test(value)) return "—";
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("es-CO");
}

function SegmentFields({ draft, setDraft, options, idPrefix }: {
  draft: SegmentDraft;
  setDraft: (next: SegmentDraft) => void;
  options: SegmentOption[];
  idPrefix: string;
}) {
  const supervisors = options.find((option) => String(option.id) === draft.host_org_id)?.supervisors ?? [];
  const field = (key: keyof SegmentDraft, label: string, input: ReactNode) => (
    <div className="field"><label htmlFor={`${idPrefix}-${key}`}>{label}</label>{input}</div>
  );
  const set = (key: keyof SegmentDraft) => (event: { target: { value: string } }) =>
    setDraft({ ...draft, [key]: event.target.value, ...(key === "host_org_id" ? { workplace_supervisor_id: "" } : {}) });
  return (
    <div className="segment-form-grid">
      {field("host_org_id", "Organización", (
        <select id={`${idPrefix}-host_org_id`} required value={draft.host_org_id} onChange={set("host_org_id")}>
          <option value="">Selecciona…</option>
          {options.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}
        </select>
      ))}
      {field("workplace_supervisor_id", "Supervisor laboral", (
        <select id={`${idPrefix}-workplace_supervisor_id`} required value={draft.workplace_supervisor_id}
          onChange={set("workplace_supervisor_id")} disabled={!draft.host_org_id}>
          <option value="">Selecciona…</option>
          {supervisors.map((person) => <option key={person.id} value={person.id}>{person.display_name}</option>)}
        </select>
      ))}
      {field("unit", "Unidad o área", <input id={`${idPrefix}-unit`} required maxLength={160} value={draft.unit} onChange={set("unit")} />)}
      {field("modality", "Modalidad", (
        <select id={`${idPrefix}-modality`} required value={draft.modality} onChange={set("modality")}>
          <option value="">Selecciona…</option>
          {Object.entries(MODALITY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      ))}
      {field("start_date", "Inicio", <input id={`${idPrefix}-start_date`} type="date" required value={draft.start_date} onChange={set("start_date")} />)}
      {field("end_date", "Fin", <input id={`${idPrefix}-end_date`} type="date" required value={draft.end_date} onChange={set("end_date")} />)}
      {field("expected_hours", "Horas esperadas (opcional)", (
        <input id={`${idPrefix}-expected_hours`} type="number" min="0.5" step="0.5" value={draft.expected_hours} onChange={set("expected_hours")} />
      ))}
      <div className="field segment-form-wide"><label htmlFor={`${idPrefix}-responsibilities`}>Responsabilidades</label>
        <textarea id={`${idPrefix}-responsibilities`} required maxLength={5000} rows={3} value={draft.responsibilities} onChange={set("responsibilities")} />
      </div>
    </div>
  );
}

export default function PlacementSegments({ dossier, onChanged }: Props) {
  const pid = dossier.placement.id;
  const segments = dossier.segments ?? [];
  const transfers = dossier.transfers ?? [];
  const reviews = dossier.experience_reviews ?? [];
  const caps = dossier.capabilities;
  const isActive = dossier.placement.state === "ACTIVE";
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [options, setOptions] = useState<SegmentOption[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<SegmentDraft>(EMPTY_SEGMENT_DRAFT);
  const [panel, setPanel] = useState<Panel>(null);
  const [references, setReferences] = useState<Record<number, string>>({});
  const [endForm, setEndForm] = useState({ ended_on: todayIso(), reason_shared: "", reason_internal: "", recognition: "ACCEPTED_HOURS_RECOGNIZED" as WorkRecognition, note: "" });
  const [destination, setDestination] = useState<SegmentDraft>(EMPTY_SEGMENT_DRAFT);
  const [experience, setExperience] = useState({ decision: "APPROVED" as "APPROVED" | "CHANGES_REQUIRED", rationale: "" });

  if (segments.length === 0 && !caps.manage_segments) return null;

  async function run(key: string, action: () => Promise<unknown>, success: string) {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      setPanel(null);
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible completar la acción.");
    } finally {
      setBusy(null);
    }
  }

  async function ensureOptions() {
    if (options !== null) return;
    try {
      setOptions(await api.listSegmentOptions(pid));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible cargar organizaciones y supervisores.");
      setOptions([]);
    }
  }

  function openPanel(segmentId: number, kind: "terminate" | "transfer" | "cancel") {
    setPanel({ segmentId, kind });
    setEndForm({ ended_on: todayIso(), reason_shared: "", reason_internal: "", recognition: "ACCEPTED_HOURS_RECOGNIZED", note: "" });
    setDestination({ ...EMPTY_SEGMENT_DRAFT, start_date: todayIso() });
    if (kind === "transfer") void ensureOptions();
  }

  function submitCreate(event: FormEvent) {
    event.preventDefault();
    const built = buildSegmentInput(draft);
    if ("error" in built) { setError(built.error); return; }
    void run("create", () => api.createPlacementSegment(pid, built.value), "Segmento planificado. Debe cumplir sus condiciones antes de activarse.")
      .then(() => { setDraft(EMPTY_SEGMENT_DRAFT); setCreating(false); });
  }

  function submitEnd(segment: PlacementSegment, event: FormEvent) {
    event.preventDefault();
    if (!endForm.reason_shared.trim()) { setError("Indica el motivo visible para las personas relacionadas."); return; }
    if (panel?.kind === "cancel") {
      void run(`cancel-${segment.id}`, () => api.cancelPlacementSegment(pid, segment.id, endForm.reason_shared), "Segmento cancelado.");
      return;
    }
    if (panel?.kind === "terminate") {
      void run(`terminate-${segment.id}`, () => api.terminatePlacementSegment(pid, segment.id, {
        ended_on: endForm.ended_on,
        reason_shared: endForm.reason_shared,
        reason_internal: endForm.reason_internal || undefined,
        work_recognition: endForm.recognition,
        recognition_note: endForm.note || undefined,
      }), "Segmento terminado anticipadamente; su historial se conserva.");
      return;
    }
    const built = buildSegmentInput(destination);
    if ("error" in built) { setError(built.error); return; }
    void run(`transfer-${segment.id}`, () => api.transferPlacementSegment(pid, segment.id, {
      effective_date: endForm.ended_on,
      reason_shared: endForm.reason_shared,
      reason_internal: endForm.reason_internal || undefined,
      prior_work_treatment: endForm.recognition,
      destination: built.value,
    }), "Transferencia registrada. El segmento destino queda planificado hasta cumplir sus condiciones.");
  }

  const overview = hoursOverview(dossier.hours_summary);
  const blockers = segmentGateBlockers(dossier.segment_gate, dossier.placement.state === "ACTIVE");

  return (
    <BentoCard variant="content" className="dossier-wide segment-card" title="Segmentos y rotaciones"
      description="La práctica conserva su identidad académica; cada segmento registra organización, supervisión, fechas y registros propios.">
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      {overview && (
        <div className="segment-hours-overview" aria-label="Resumen de horas por estado">
          <div><span>Horas reportadas</span><strong>{formatHours(overview.reported)} h</strong></div>
          <div><span>Horas aceptadas{dossier.hours_summary?.scope === "SEGMENT" ? " (tu segmento)" : " consolidadas"}</span><strong>{formatHours(overview.accepted)} h</strong></div>
          <div><span>Pendientes de revisión</span><strong>{formatHours(overview.pending)} h</strong></div>
        </div>
      )}
      {dossier.segment_gate && blockers.length > 0 && isActive && (
        <p className="dossier-gate-note">Para finalizar falta: {blockers.join("; ")}.</p>
      )}

      {segments.length === 0 && <EmptyState message="La práctica todavía no tiene segmentos (se crea el primero al activarla)." />}
      <ol className="segment-list">
        {segments.map((segment) => {
          const pendingConditions = segment.conditions.filter((condition) => condition.status !== "SATISFIED");
          const endPanel = panel?.segmentId === segment.id ? panel.kind : null;
          return (
            <li className={`segment-item segment-${segment.status.toLowerCase()}`} key={segment.id}>
              <div className="row segment-heading">
                <strong>Segmento {segment.sequence_no} · {segment.host_org_name}{segment.unit ? ` · ${segment.unit}` : ""}</strong>
                <Badge state={segmentTone(segment.status)} label={SEGMENT_STATUS_LABELS[segment.status]}>{segment.status}</Badge>
              </div>
              <dl className="dossier-facts segment-facts">
                <div><dt>Periodo</dt><dd>{localDate(segment.start_date)} – {localDate(segment.end_date)}</dd></div>
                <div><dt>Supervisor laboral</dt><dd>{segment.workplace_supervisor_name ?? "Sin asignación registrada"}</dd></div>
                <div><dt>Modalidad</dt><dd>{segment.modality ? MODALITY_LABELS[segment.modality] : "No registrada"}</dd></div>
                <div><dt>Horas esperadas</dt><dd>{segment.expected_hours === null ? "No definidas" : `${formatHours(segment.expected_hours)} h`}</dd></div>
                <div><dt>Origen</dt><dd>{SEGMENT_ORIGIN_LABELS[segment.origin] ?? segment.origin}</dd></div>
                {segment.ended_on && <div><dt>Cierre efectivo</dt><dd>{localDate(segment.ended_on)}</dd></div>}
                {segment.work_recognition && <div><dt>Trabajo previo</dt><dd>{RECOGNITION_LABELS[segment.work_recognition]}</dd></div>}
              </dl>
              {segment.end_reason_shared && <p><strong>Motivo:</strong> {segment.end_reason_shared}</p>}
              {segment.end_reason_internal && <p className="segment-internal"><strong>Motivo confidencial (solo roles autorizados):</strong> {segment.end_reason_internal}</p>}
              {segment.recognition_note && <p className="muted">Nota de reconocimiento: {segment.recognition_note}</p>}
              <details>
                <summary>Responsabilidades y condiciones</summary>
                <p className="dossier-preserve-text">{segment.responsibilities}</p>
                {segment.conditions.length === 0 && <p className="muted">Sin condiciones de habilitación registradas.</p>}
                {segment.conditions.map((condition) => (
                  <div className="dossier-requirement" key={condition.id}>
                    <span>{formatDomainLabel(condition.kind)}{condition.reference ? ` · ${condition.reference}` : ""}{condition.confirmed_by ? ` · ${condition.confirmed_by}` : ""}</span>
                    <Badge state={segmentTone(condition.status)} label={condition.status === "SATISFIED" ? "Cumplida" : "Pendiente"}>{condition.status}</Badge>
                    {caps.confirm_segment_conditions && isActive && segment.status === "PLANNED" && condition.status === "REQUIRED" && (
                      <form className="row segment-inline-form" onSubmit={(event) => {
                        event.preventDefault();
                        const reference = (references[condition.id] ?? "").trim();
                        if (!reference) { setError("Indica la referencia del documento verificado."); return; }
                        void run(`cond-${condition.id}`, () => api.confirmSegmentCondition(pid, segment.id, condition.id, reference), "Condición confirmada.");
                      }}>
                        <label className="sr-only" htmlFor={`cond-${condition.id}`}>Referencia verificada</label>
                        <input id={`cond-${condition.id}`} placeholder="Referencia verificada" maxLength={500}
                          value={references[condition.id] ?? ""} onChange={(event) => setReferences({ ...references, [condition.id]: event.target.value })} />
                        <button className="btn secondary" type="submit" disabled={busy !== null}>Confirmar condición</button>
                      </form>
                    )}
                  </div>
                ))}
                {segment.status_history.length > 0 && (
                  <ol className="segment-history" aria-label={`Historial del segmento ${segment.sequence_no}`}>
                    {segment.status_history.map((entry, index) => (
                      <li key={index}>{formatHistoryDate(entry.changed_at)} · {entry.from_status ? SEGMENT_STATUS_LABELS[entry.from_status] : "—"} → {SEGMENT_STATUS_LABELS[entry.to_status]}{entry.actor_name ? ` · ${entry.actor_name}` : ""}</li>
                    ))}
                  </ol>
                )}
              </details>

              {caps.manage_segments && isActive && segment.status === "PLANNED" && (
                <div className="row segment-actions">
                  <button className="btn" type="button" disabled={busy !== null || pendingConditions.length > 0}
                    title={pendingConditions.length ? "Hay condiciones pendientes" : undefined}
                    onClick={() => void run(`activate-${segment.id}`, () => api.activatePlacementSegment(pid, segment.id), "Segmento activado.")}>
                    {busy === `activate-${segment.id}` ? <Spinner /> : "Activar segmento"}
                  </button>
                  <button className="btn secondary" type="button" onClick={() => openPanel(segment.id, "cancel")}>Cancelar segmento</button>
                  {pendingConditions.length > 0 && <span className="muted">Condiciones pendientes: {pendingConditions.map((c) => formatDomainLabel(c.kind)).join(", ")}</span>}
                </div>
              )}
              {caps.manage_segments && isActive && segment.status === "ACTIVE" && (
                <div className="row segment-actions">
                  <button className="btn secondary" type="button" disabled={busy !== null}
                    onClick={() => void run(`complete-${segment.id}`, () => api.completePlacementSegment(pid, segment.id), "Segmento completado. El siguiente no se activa automáticamente.")}>
                    {busy === `complete-${segment.id}` ? <Spinner /> : "Completar segmento"}
                  </button>
                  <button className="btn secondary" type="button" onClick={() => openPanel(segment.id, "transfer")}>Transferir</button>
                  <button className="btn secondary" type="button" onClick={() => openPanel(segment.id, "terminate")}>Terminar anticipadamente</button>
                </div>
              )}
              {endPanel && (
                <form className="segment-panel" onSubmit={(event) => submitEnd(segment, event)}
                  aria-label={endPanel === "transfer" ? "Transferir segmento" : endPanel === "terminate" ? "Terminar segmento" : "Cancelar segmento"}>
                  {endPanel !== "cancel" && (
                    <div className="segment-form-grid">
                      <div className="field"><label htmlFor={`end-date-${segment.id}`}>{endPanel === "transfer" ? "Fecha de efecto" : "Fecha de cierre"}</label>
                        <input id={`end-date-${segment.id}`} type="date" required value={endForm.ended_on} onChange={(event) => setEndForm({ ...endForm, ended_on: event.target.value })} /></div>
                      <div className="field"><label htmlFor={`recognition-${segment.id}`}>Trabajo previo</label>
                        <select id={`recognition-${segment.id}`} value={endForm.recognition} onChange={(event) => setEndForm({ ...endForm, recognition: event.target.value as WorkRecognition })}>
                          {Object.entries(RECOGNITION_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                        </select></div>
                    </div>
                  )}
                  <div className="field"><label htmlFor={`reason-${segment.id}`}>Motivo visible para las personas relacionadas</label>
                    <textarea id={`reason-${segment.id}`} required maxLength={1000} rows={2} value={endForm.reason_shared} onChange={(event) => setEndForm({ ...endForm, reason_shared: event.target.value })} /></div>
                  {endPanel !== "cancel" && (
                    <div className="field"><label htmlFor={`internal-${segment.id}`}>Motivo confidencial (opcional, solo roles internos autorizados)</label>
                      <textarea id={`internal-${segment.id}`} maxLength={3000} rows={2} value={endForm.reason_internal} onChange={(event) => setEndForm({ ...endForm, reason_internal: event.target.value })} /></div>
                  )}
                  {endPanel === "terminate" && (
                    <div className="field"><label htmlFor={`note-${segment.id}`}>Nota sobre el reconocimiento (opcional)</label>
                      <input id={`note-${segment.id}`} maxLength={1000} value={endForm.note} onChange={(event) => setEndForm({ ...endForm, note: event.target.value })} /></div>
                  )}
                  {endPanel === "transfer" && (
                    <fieldset className="segment-destination"><legend>Segmento destino</legend>
                      {options === null ? <Spinner /> : <SegmentFields draft={destination} setDraft={setDestination} options={options} idPrefix={`dest-${segment.id}`} />}
                    </fieldset>
                  )}
                  <div className="row">
                    <button className="btn" type="submit" disabled={busy !== null}>{busy ? <Spinner /> : endPanel === "transfer" ? "Registrar transferencia" : endPanel === "terminate" ? "Terminar segmento" : "Cancelar segmento"}</button>
                    <button className="btn link" type="button" onClick={() => setPanel(null)}>Volver</button>
                  </div>
                </form>
              )}
            </li>
          );
        })}
      </ol>

      {caps.manage_segments && isActive && (
        creating ? (
          <form className="segment-panel" onSubmit={submitCreate} aria-label="Planificar nuevo segmento">
            <h3>Planificar nuevo segmento</h3>
            {options === null ? <Spinner /> : <SegmentFields draft={draft} setDraft={setDraft} options={options} idPrefix="new-segment" />}
            <div className="row">
              <button className="btn" type="submit" disabled={busy !== null}>{busy === "create" ? <Spinner /> : "Guardar segmento planificado"}</button>
              <button className="btn link" type="button" onClick={() => setCreating(false)}>Volver</button>
            </div>
          </form>
        ) : (
          <button className="btn secondary" type="button" onClick={() => { setCreating(true); void ensureOptions(); }}>Planificar nuevo segmento</button>
        )
      )}

      {transfers.length > 0 && (
        <section className="segment-transfers" aria-label="Transferencias registradas">
          <h3>Transferencias</h3>
          <ul>
            {transfers.map((transfer) => (
              <li key={transfer.id}>
                <strong>Segmento {transfer.from_sequence_no} → segmento {transfer.to_sequence_no}</strong>
                <span> · efecto {localDate(transfer.effective_date)} · aprobada por {transfer.approved_by} el {formatHistoryDate(transfer.approved_at)}</span>
                <p>{transfer.reason_shared} · {RECOGNITION_LABELS[transfer.prior_work_treatment]}</p>
                {transfer.reason_internal && <p className="segment-internal"><strong>Motivo confidencial:</strong> {transfer.reason_internal}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {(reviews.length > 0 || (caps.review_combined_experience && dossier.segment_gate?.combined_review_required)) && (
        <section className="segment-experience" aria-label="Revisión de la experiencia combinada">
          <h3>Revisión académica de la experiencia combinada</h3>
          {reviews.map((review) => (
            <p key={review.id}><Badge state={review.decision === "APPROVED" ? "APPROVED" : "REQUIRED"} label={review.decision === "APPROVED" ? "Aprobada" : "Requiere cambios"}>{review.decision}</Badge> {review.rationale} · {review.reviewer} · {formatHistoryDate(review.reviewed_at)}</p>
          ))}
          {caps.review_combined_experience && isActive && dossier.segment_gate?.combined_review_required && (
            dossier.segment_gate.open_segments > 0
              ? <p className="muted">La revisión se habilita cuando todos los segmentos estén cerrados.</p>
              : (
                <form onSubmit={(event) => {
                  event.preventDefault();
                  if (!experience.rationale.trim()) { setError("Escribe la justificación de la revisión."); return; }
                  void run("experience", () => api.recordExperienceReview(pid, experience.decision, experience.rationale.trim()), "Revisión académica registrada.");
                }}>
                  <div className="segment-form-grid">
                    <div className="field"><label htmlFor="experience-decision">Decisión</label>
                      <select id="experience-decision" value={experience.decision} onChange={(event) => setExperience({ ...experience, decision: event.target.value as "APPROVED" | "CHANGES_REQUIRED" })}>
                        <option value="APPROVED">Aprobar experiencia combinada</option>
                        <option value="CHANGES_REQUIRED">Requiere cambios</option>
                      </select></div>
                    <div className="field segment-form-wide"><label htmlFor="experience-rationale">Justificación</label>
                      <textarea id="experience-rationale" required maxLength={3000} rows={2} value={experience.rationale} onChange={(event) => setExperience({ ...experience, rationale: event.target.value })} /></div>
                  </div>
                  <button className="btn" type="submit" disabled={busy !== null}>Registrar revisión</button>
                </form>
              )
          )}
        </section>
      )}
    </BentoCard>
  );
}
