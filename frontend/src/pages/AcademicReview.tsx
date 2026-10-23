import { useEffect, useState } from "react";
import * as api from "../api";
import type { PendingAcademic } from "../api";
import { Alert, Badge, EmptyState, PageHeader, Spinner } from "../components/ui";

export default function AcademicReview() {
  const [items, setItems] = useState<PendingAcademic[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  async function reload() {
    setError(null);
    try {
      setItems(await api.listPendingAcademic());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
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
