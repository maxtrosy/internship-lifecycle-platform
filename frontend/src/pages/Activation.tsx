import { useEffect, useState } from "react";
import * as api from "../api";
import { useConfirm } from "../components/overlays";
import type { ActivationStatus } from "../api";
import { Alert, Badge, BentoCard, EmptyState, PageHeader, Spinner, formatDomainLabel } from "../components/ui";

type Row = { id: number; state: string; display_name: string; program_code: string; opportunity_title: string };

export default function Activation() {
  const confirm = useConfirm();
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
      // Fetch every activation status in parallel instead of one request per
      // loop iteration; a single failure still rejects the whole reload.
      const loaded = await Promise.all(list.map((r) => api.activationStatus(r.id)));
      const map: Record<number, ActivationStatus> = {};
      list.forEach((r, index) => { map[r.id] = loaded[index]; });
      setStatuses(map);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function activate(row: Row) {
    if (!(await confirm({ title: "¿Activar la práctica?", message: `${row.display_name} · ${row.opportunity_title}. El backend vuelve a comprobar las condiciones antes de activar.`, confirmLabel: "Activar práctica" }))) return;
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
      <PageHeader eyebrow="Ciclo de vida" title="Activación de prácticas" description="Consulta las condiciones obligatorias. El sistema las comprobará de nuevo antes de activar." />
      {error && <Alert kind="error">{error}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}
      {rows === null && !error && <div className="empty"><Spinner /> Cargando…</div>}
      {rows !== null && rows.length === 0 && <EmptyState message="No hay prácticas en etapa de documentación." />}
      {rows !== null && rows.map((r) => {
        const st = statuses[r.id];
        return (
          <BentoCard variant="task" className="activation-card" key={r.id}>
            <div className="activation-row">
              <div className="activation-identity">
                <h3>{r.display_name}</h3>
                <p className="muted">{r.opportunity_title} · {r.program_code}</p>
              </div>
              <Badge>{r.state}</Badge>
              <div className="activation-actions">
                <button className="btn secondary" type="button" aria-expanded={open === r.id} aria-controls={`activation-conditions-${r.id}`}
                  onClick={() => setOpen(open === r.id ? null : r.id)}>
                  {open === r.id ? "Ocultar condiciones" : "Ver condiciones"}
                </button>
                <button className="btn" type="button" disabled={!st?.ready_to_activate}
                  aria-describedby={`activation-readiness-${r.id}`} onClick={() => activate(r)}>
                  Activar
                </button>
              </div>
              <p id={`activation-readiness-${r.id}`} className={`activation-readiness${st?.ready_to_activate ? " is-ready" : ""}`}>
                {!st ? "Comprobando condiciones…"
                  : st.ready_to_activate ? "Cumple todas las condiciones obligatorias."
                    : `No se puede activar todavía. Pendiente: ${st.unmet.map(formatDomainLabel).join(", ") || "condiciones sin detalle"}.`}
              </p>
            </div>
            {open === r.id && st && (
              <div className="activation-conditions" id={`activation-conditions-${r.id}`}>
                <div className="table-scroll" tabIndex={0} aria-label={`Condiciones para ${r.opportunity_title}`}><table>
                  <thead><tr><th scope="col">Requisito</th><th scope="col">Estado</th></tr></thead>
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
