import { useEffect, useState } from "react";
import * as api from "../api";
import type { ActivationStatus } from "../api";
import { Alert, Badge, BentoCard, EmptyState, PageHeader, Spinner, formatDomainLabel } from "../components/ui";

type Row = { id: number; state: string; display_name: string; program_code: string; opportunity_title: string };

export default function Activation() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [statuses, setStatuses] = useState<Record<number, ActivationStatus>>({});
  const [open, setOpen] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function reload() {
    setError(null);
    try {
      const list = await api.listPendingActivation();
      setRows(list);
      const map: Record<number, ActivationStatus> = {};
      for (const r of list) map[r.id] = await api.activationStatus(r.id);
      setStatuses(map);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function activate(row: Row) {
    if (!window.confirm(`¿Activar la práctica de ${row.display_name} para ${row.opportunity_title}?`)) return;
    setError(null);
    setMessage(null);
    try {
      await api.activatePlacement(row.id);
      setMessage(`La práctica de ${row.display_name} para ${row.opportunity_title} fue activada.`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="page-stack">
      <PageHeader eyebrow="CICLO DE VIDA" title="Activación de prácticas" description="Consulta las condiciones obligatorias. El sistema las comprobará de nuevo antes de activar." />
      {error && <Alert kind="error">{error}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}
      {rows === null && !error && <div className="empty"><Spinner /> Cargando…</div>}
      {rows !== null && rows.length === 0 && <EmptyState message="No hay prácticas en etapa de documentación." />}
      {rows !== null && rows.map((r) => {
        const st = statuses[r.id];
        return (
          <BentoCard variant="task" className="activation-card" key={r.id}>
            <div className="row">
              <div className="spacer">
                <h3>{r.display_name} · {r.program_code}</h3>
                <p className="muted">{r.opportunity_title}</p>
              </div>
              <Badge>{r.state}</Badge>
              <button className="btn secondary" onClick={() => setOpen(open === r.id ? null : r.id)}>
                Condiciones
              </button>
              <button className="btn" disabled={!st?.ready_to_activate} onClick={() => activate(r)}>
                Activar
              </button>
            </div>
            {open === r.id && st && (
              <div style={{ marginTop: 8 }}>
                <p className="muted">
                  {st.ready_to_activate ? "Cumple todas las condiciones." : `Pendiente: ${st.unmet.map(formatDomainLabel).join(", ") || "—"}`}
                </p>
                <div className="table-scroll" tabIndex={0} aria-label={`Condiciones para ${r.opportunity_title}`}><table>
                  <thead><tr><th>Requisito</th><th>Estado</th></tr></thead>
                  <tbody>
                    {st.items.map((it) => (
                      <tr key={it.id}><td>{formatDomainLabel(it.kind)}</td><td><Badge>{it.status}</Badge></td></tr>
                    ))}
                  </tbody>
                </table></div>
              </div>
            )}
          </BentoCard>
        );
      })}
    </div>
  );
}
