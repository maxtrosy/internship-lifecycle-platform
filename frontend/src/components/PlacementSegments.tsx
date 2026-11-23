import { useState, type FormEvent } from "react";
import * as api from "../api";
import type { PlacementDossier, PlacementSegment, SegmentOption, WorkRecognition } from "../api";
import { Alert, Badge, BentoCard, EmptyState, Spinner } from "./ui";
import { DisabledReason, Drawer } from "./overlays";
import { formatHistoryDate } from "../history";
import {
  EMPTY_SEGMENT_DRAFT,
  RECOGNITION_LABELS,
  buildSegmentInput,
  segmentGateBlockers,
  todayIso,
  type SegmentDraft,
} from "../segments";
import { SegmentFields } from "./segments/SegmentFields";
import { SegmentHours } from "./segments/SegmentHours";
import { SegmentItem, type SegmentPanelKind } from "./segments/SegmentItem";
import { SegmentTransfers } from "./segments/SegmentTransfers";

type Props = { dossier: PlacementDossier; onChanged: () => void };
type Panel = { segmentId: number; kind: SegmentPanelKind } | null;



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
  const [endForm, setEndForm] = useState({ ended_on: todayIso(), reason_shared: "", reason_internal: "", recognition: "ACCEPTED_HOURS_RECOGNIZED" as WorkRecognition, note: "" });
  const [destination, setDestination] = useState<SegmentDraft>(EMPTY_SEGMENT_DRAFT);
  const [experience, setExperience] = useState({ decision: "APPROVED" as "APPROVED" | "CHANGES_REQUIRED", rationale: "" });

  if (segments.length === 0 && !caps.manage_segments) return null;

  async function run(key: string, action: () => Promise<unknown>, success: string): Promise<boolean> {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      setPanel(null);
      setCreating(false);
      onChanged();
      return true;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible completar la acción.");
      return false;
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

  function openPanel(segmentId: number, kind: SegmentPanelKind) {
    setCreating(false);
    setError(null);
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
      .then((saved) => { if (saved) setDraft(EMPTY_SEGMENT_DRAFT); });
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

  const blockers = segmentGateBlockers(dossier.segment_gate, dossier.placement.state === "ACTIVE");
  const panelSegment = panel ? segments.find((segment) => segment.id === panel.segmentId) ?? null : null;
  const drawerOpen = panelSegment !== null || creating;
  const panelTitle = creating ? "Planificar nuevo segmento"
    : panel?.kind === "transfer" ? "Transferir segmento"
      : panel?.kind === "terminate" ? "Terminar segmento anticipadamente" : "Cancelar segmento";
  const panelSubmit = creating ? "Guardar segmento planificado"
    : panel?.kind === "transfer" ? "Registrar transferencia"
      : panel?.kind === "terminate" ? "Terminar segmento" : "Cancelar segmento";
  const formId = `segment-form-${pid}`;

  function closeDrawer() {
    setPanel(null);
    setCreating(false);
    setError(null);
  }

  return (
    <BentoCard variant="content" className="dossier-wide segment-card" title="Segmentos y rotaciones"
      description="La práctica conserva su identidad académica; cada segmento registra organización, supervisión, fechas y registros propios.">
      {error && !drawerOpen && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      <SegmentHours dossier={dossier} />

      {dossier.segment_gate && blockers.length > 0 && isActive && (
        <div className="segment-gate">
          <p className="segment-gate-title">Para finalizar la práctica falta:</p>
          <ul>{blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul>
        </div>
      )}

      {segments.length === 0 && <EmptyState icon="segment" message="La práctica todavía no tiene segmentos (se crea el primero al activarla)." />}
      <ol className="segment-list" aria-label="Segmentos de la práctica">
        {segments.map((segment) => (
          <SegmentItem key={segment.id} pid={pid} segment={segment} dossier={dossier} busy={busy} run={run}
            onOpenPanel={openPanel} onError={setError} />
        ))}
      </ol>

      {caps.manage_segments && isActive && (
        <div className="section-footer-actions">
          <button className="btn secondary" type="button" onClick={() => { setPanel(null); setCreating(true); void ensureOptions(); }}>Planificar nuevo segmento</button>
        </div>
      )}

      <Drawer open={drawerOpen} title={panelTitle} onClose={closeDrawer}
        description={panelSegment ? `Segmento ${panelSegment.sequence_no} · ${panelSegment.host_org_name}. El historial del segmento se conserva.` : "El segmento queda planificado hasta cumplir sus condiciones de habilitación."}
        footer={<>
          <button className="btn secondary" type="button" onClick={closeDrawer}>Volver</button>
          <button className={`btn${panel?.kind === "terminate" || panel?.kind === "cancel" ? " danger" : ""}`} type="submit" form={formId} disabled={busy !== null}>
            {busy ? <Spinner /> : panelSubmit}
          </button>
        </>}>
        {error && <Alert kind="error">{error}</Alert>}
        {creating && (
          <form id={formId} onSubmit={submitCreate} aria-label="Planificar nuevo segmento">
            {options === null ? <Spinner /> : <SegmentFields draft={draft} setDraft={setDraft} options={options} idPrefix="new-segment" />}
          </form>
        )}
        {panelSegment && panel && (
          <form id={formId} onSubmit={(event) => submitEnd(panelSegment, event)}
            aria-label={panel.kind === "transfer" ? "Transferir segmento" : panel.kind === "terminate" ? "Terminar segmento" : "Cancelar segmento"}>
            {panel.kind !== "cancel" && (
              <div className="segment-form-grid">
                <div className="field"><label htmlFor={`end-date-${panelSegment.id}`}>{panel.kind === "transfer" ? "Fecha de efecto" : "Fecha de cierre"}</label>
                  <input id={`end-date-${panelSegment.id}`} type="date" required value={endForm.ended_on} onChange={(event) => setEndForm({ ...endForm, ended_on: event.target.value })} /></div>
                <div className="field"><label htmlFor={`recognition-${panelSegment.id}`}>Trabajo previo</label>
                  <select id={`recognition-${panelSegment.id}`} value={endForm.recognition} onChange={(event) => setEndForm({ ...endForm, recognition: event.target.value as WorkRecognition })}>
                    {Object.entries(RECOGNITION_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select></div>
              </div>
            )}
            <div className="field"><label htmlFor={`reason-${panelSegment.id}`}>Motivo visible para las personas relacionadas</label>
              <textarea id={`reason-${panelSegment.id}`} required maxLength={1000} rows={3} value={endForm.reason_shared} onChange={(event) => setEndForm({ ...endForm, reason_shared: event.target.value })} /></div>
            {panel.kind !== "cancel" && (
              <div className="field"><label htmlFor={`internal-${panelSegment.id}`}>Motivo confidencial (opcional)</label>
                <p className="field-hint" id={`internal-${panelSegment.id}-hint`}>Solo lo consultan los roles internos autorizados.</p>
                <textarea id={`internal-${panelSegment.id}`} aria-describedby={`internal-${panelSegment.id}-hint`} maxLength={3000} rows={2} value={endForm.reason_internal} onChange={(event) => setEndForm({ ...endForm, reason_internal: event.target.value })} /></div>
            )}
            {panel.kind === "terminate" && (
              <div className="field"><label htmlFor={`note-${panelSegment.id}`}>Nota sobre el reconocimiento (opcional)</label>
                <input id={`note-${panelSegment.id}`} maxLength={1000} value={endForm.note} onChange={(event) => setEndForm({ ...endForm, note: event.target.value })} /></div>
            )}
            {panel.kind === "transfer" && (
              <fieldset className="segment-destination"><legend>Segmento destino</legend>
                {options === null ? <Spinner /> : <SegmentFields draft={destination} setDraft={setDestination} options={options} idPrefix={`dest-${panelSegment.id}`} />}
              </fieldset>
            )}
          </form>
        )}
      </Drawer>

      {transfers.length > 0 && <SegmentTransfers pid={pid} transfers={transfers} />}

      {(reviews.length > 0 || (caps.review_combined_experience && dossier.segment_gate?.combined_review_required)) && (
        <section className="segment-experience" aria-labelledby={`experience-${pid}`}>
          <h3 id={`experience-${pid}`}>Revisión académica de la experiencia combinada</h3>
          {reviews.length > 0 && <ol className="experience-review-list">
            {reviews.map((review) => (
              <li key={review.id}>
                <Badge state={review.decision === "APPROVED" ? "APPROVED" : "REQUIRED"} label={review.decision === "APPROVED" ? "Aprobada" : "Requiere cambios"}>{review.decision}</Badge>
                <p>{review.rationale}</p>
                <span className="muted">{review.reviewer} · {formatHistoryDate(review.reviewed_at)}</span>
              </li>
            ))}
          </ol>}
          {caps.review_combined_experience && isActive && dossier.segment_gate?.combined_review_required && (
            dossier.segment_gate.open_segments > 0
              ? <DisabledReason id={`experience-reason-${pid}`}>La revisión se habilita cuando todos los segmentos estén cerrados.</DisabledReason>
              : (
                <form className="experience-form" onSubmit={(event) => {
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
                      <textarea id="experience-rationale" required maxLength={3000} rows={3} value={experience.rationale} onChange={(event) => setExperience({ ...experience, rationale: event.target.value })} /></div>
                  </div>
                  <div><button className="btn" type="submit" disabled={busy !== null}>Registrar revisión</button></div>
                </form>
              )
          )}
        </section>
      )}
    </BentoCard>
  );
}
