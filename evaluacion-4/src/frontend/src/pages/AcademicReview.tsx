import { useEffect, useState } from "react";
import * as api from "../api";
import type { PendingAcademic, PendingEligibilityReview } from "../api";
import { Alert, Badge, EmptyState, PageHeader, Spinner } from "../components/ui";

export default function AcademicReview() {
  const [items, setItems] = useState<PendingAcademic[] | null>(null);
  const [eligibilityItems, setEligibilityItems] = useState<PendingEligibilityReview[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [eligibilityRationale, setEligibilityRationale] = useState<Record<number, string>>({});

  async function reload() {
    setError(null);
    try {
      const [academic, eligibility] = await Promise.all([
        api.listPendingAcademic(), api.listPendingEligibilityReviews(),
      ]);
      setItems(academic);
      setEligibilityItems(eligibility);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function decideEligibility(item: PendingEligibilityReview, decision: "ELIGIBLE" | "INELIGIBLE") {
    const rationale = eligibilityRationale[item.id]?.trim() ?? "";
    if (!rationale) {
      setError("Registra la justificación de la decisión académica.");
      return;
    }
    const decisionLabel = decision === "ELIGIBLE" ? "elegible" : "no elegible";
    if (!window.confirm(`Marcar a ${item.display_name} como ${decisionLabel} para ${item.opportunity_title}?`)) return;
    setBusy(item.id);
    setError(null);
    setSuccess(null);
    try {
      await api.reviewEligibility(item.id, { decision, rationale });
      setEligibilityRationale((current) => { const next = { ...current }; delete next[item.id]; return next; });
      setSuccess(`Se registró la decisión académica para ${item.display_name}.`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  function profileSummary(value: unknown): string {
    if (typeof value !== "object" || value === null || Array.isArray(value)) return "Perfil académico sin detalle disponible.";
    const inputs = (value as Record<string, unknown>).inputs;
    if (typeof inputs !== "object" || inputs === null || Array.isArray(inputs)) return "Perfil académico sin detalle disponible.";
    const facts = inputs as Record<string, unknown>;
    const credits = typeof facts.credits === "number" ? `${facts.credits} créditos` : "créditos no registrados";
    const level = typeof facts.academic_level === "number" ? `nivel ${facts.academic_level}` : "nivel no registrado";
    return `${credits} · ${level}`;
  }

  useEffect(() => {
    reload();
  }, []);

  async function approve(item: PendingAcademic) {
    if (!window.confirm(`¿Aprobar la selección de ${item.display_name} para ${item.opportunity_title}?`)) return;
    const pid = item.id;
    setBusy(pid);
    setError(null);
    setSuccess(null);
    try {
      await api.approveAcademic(pid);
      setSuccess(`Se aprobó la selección de ${item.display_name} para ${item.opportunity_title}.`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function reject(item: PendingAcademic) {
    const pid = item.id;
    if (!reason.trim()) {
      setError("Escribe un motivo para rechazar.");
      return;
    }
    if (!window.confirm(`¿Rechazar la selección de ${item.display_name} para ${item.opportunity_title}?`)) return;
    setBusy(pid);
    setError(null);
    setSuccess(null);
    try {
      await api.rejectAcademic(pid, reason);
      setReason("");
      setRejectingId(null);
      setSuccess(`Se rechazó la selección de ${item.display_name} para ${item.opportunity_title}.`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader eyebrow="COORDINACIÓN" title="Revisión académica" description="Al aprobar, el sistema fija las políticas vigentes del programa para activar y cerrar la práctica." />

      {success && <Alert kind="success">{success}</Alert>}
      {error && <Alert kind="error">{error}</Alert>}

      {eligibilityItems === null && !error && <div className="empty"><Spinner /> Cargando revisiones de elegibilidad…</div>}
      {eligibilityItems !== null && eligibilityItems.length === 0 && <EmptyState message="No hay postulaciones pendientes de revisión de elegibilidad." />}
      {!!eligibilityItems?.length && (
        <div className="card queue-card">
          <div className="section-heading"><div><span className="eyebrow">ELEGIBILIDAD</span><h2>Revisión manual pendiente</h2><p>El resultado requiere una decisión documentada de la coordinación del programa.</p></div></div>
          <div className="table-scroll" tabIndex={0} aria-label="Postulaciones pendientes de revisión de elegibilidad"><table className="eligibility-review-table">
            <thead><tr><th>Estudiante</th><th>Programa y oportunidad</th><th>Datos registrados</th><th>Decisión y fundamento</th></tr></thead>
            <tbody>{eligibilityItems.map((item) => (
              <tr key={item.id}>
                <td data-label="Estudiante">{item.display_name}</td>
                <td data-label="Programa y oportunidad">{item.program_code}<br /><span className="muted">{item.opportunity_title}</span></td>
                <td data-label="Datos registrados">{profileSummary(item.eligibility_result)}<br /><span className="muted">Política v{item.policy_version ?? "sin versión"}</span></td>
                <td data-label="Decisión y fundamento">
                  <div className="field" style={{ minWidth: 250 }}>
                    <label htmlFor={`eligibility-rationale-${item.id}`}>Fundamento de la decisión</label>
                    <textarea id={`eligibility-rationale-${item.id}`} value={eligibilityRationale[item.id] ?? ""}
                      maxLength={2000} rows={3} onChange={(event) => setEligibilityRationale((current) => ({ ...current, [item.id]: event.target.value }))} />
                  </div>
                  <div className="row" style={{ marginTop: 8 }}>
                    <button className="btn" type="button" disabled={busy === item.id || !eligibilityRationale[item.id]?.trim()}
                      onClick={() => void decideEligibility(item, "ELIGIBLE")}>{busy === item.id ? <Spinner /> : "Marcar elegible"}</button>
                    <button className="btn danger" type="button" disabled={busy === item.id || !eligibilityRationale[item.id]?.trim()}
                      onClick={() => void decideEligibility(item, "INELIGIBLE")}>Marcar no elegible</button>
                  </div>
                </td>
              </tr>
            ))}</tbody>
          </table></div>
        </div>
      )}

      {items === null && !error && <div className="empty"><Spinner /> Cargando…</div>}
      {items !== null && items.length === 0 && <EmptyState message="No hay selecciones pendientes de revisión." />}
      {items !== null && items.length > 0 && (
        <div className="card queue-card">
          <div className="section-heading"><div><span className="eyebrow">COLA DE REVISIÓN</span><h2>Selecciones pendientes</h2><p>{items.length} {items.length === 1 ? "selección requiere" : "selecciones requieren"} una decisión académica.</p></div></div>
          <div className="table-scroll" tabIndex={0} aria-label="Selecciones pendientes"><table>
            <thead>
              <tr>
                <th>Estudiante</th>
                <th>Programa</th>
                <th>Oportunidad</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id}>
                  <td>{p.display_name}</td>
                  <td>{p.program_code}</td>
                  <td>{p.opportunity_title}</td>
                  <td>
                    {rejectingId === p.id ? (
                      <div className="row">
                        <input
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                          placeholder="Motivo del rechazo"
                          aria-label="Motivo del rechazo"
                          style={{ minWidth: 200 }}
                        />
                        <button className="btn danger" disabled={busy === p.id} onClick={() => reject(p)}>
                          {busy === p.id ? <Spinner /> : "Rechazar"}
                        </button>
                        <button className="btn secondary" onClick={() => setRejectingId(null)}>Cancelar</button>
                      </div>
                    ) : (
                      <div className="row">
                        <Badge>{p.state}</Badge>
                        <button className="btn" disabled={busy === p.id} onClick={() => approve(p)}>
                          {busy === p.id ? <Spinner /> : "Aprobar"}
                        </button>
                        <button className="btn secondary" onClick={() => setRejectingId(p.id)}>Rechazar</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
      )}
    </div>
  );
}
