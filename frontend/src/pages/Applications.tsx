import { useEffect, useMemo, useState } from "react";
import * as api from "../api";
import type { Application } from "../api";
import EligibilitySummary from "../components/EligibilitySummary";
import { Alert, Badge, EmptyState, PageHeader, Skeleton, formatDomainLabel } from "../components/ui";
import type { SectionId } from "../components/Layout";
import { errorMessage } from "../useAsyncAction";

const ALL = "ALL";

export default function Applications({ onNavigate }: { onNavigate: (section: SectionId) => void }) {
  const [items, setItems] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [state, setState] = useState(ALL);

  useEffect(() => {
    api.listApplications()
      .then(setItems)
      .catch((cause: unknown) => setError(errorMessage(cause, "No fue posible cargar tus postulaciones.")));
  }, []);

  // Filters are derived from the states actually present, so no state is invented.
  const states = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of items ?? []) counts.set(item.state, (counts.get(item.state) ?? 0) + 1);
    return [...counts.entries()];
  }, [items]);
  const visible = useMemo(() => (items ?? []).filter((item) => state === ALL || item.state === state), [items, state]);
  const withPlacement = (items ?? []).filter((item) => item.placement_id).length;

  return (
    <div className="page-stack">
      <PageHeader eyebrow="Mi proceso" title="Mis postulaciones" description="Consulta las decisiones de selección, el estado de tu práctica y el resultado de elegibilidad." />

      {error && <Alert kind="error">{error}</Alert>}
      {items === null && !error && <Skeleton lines={4} />}
      {items !== null && items.length === 0 && (
        <EmptyState icon="inbox" message="Todavía no tienes postulaciones." action={<button className="btn" type="button" onClick={() => onNavigate("opportunities")}>Explorar oportunidades</button>} />
      )}
      {items !== null && items.length > 0 && (
        <section className="data-panel applications-card" aria-labelledby="applications-title">
          <div className="data-panel-header">
            <div>
              <h2 id="applications-title">Historial de postulaciones</h2>
              <p className="data-panel-meta">Abre el detalle de elegibilidad para consultar los criterios evaluados.</p>
            </div>
            {states.length > 1 && (
              <div className="toolbar">
                <div className="field state-filter">
                  <label htmlFor="applications-state">Estado</label>
                  <select id="applications-state" value={state} onChange={(event) => setState(event.target.value)}>
                    <option value={ALL}>Todos ({items.length})</option>
                    {states.map(([code, count]) => <option key={code} value={code}>{formatDomainLabel(code)} ({count})</option>)}
                  </select>
                </div>
              </div>
            )}
          </div>
          <p className="state-summary">
            <span><strong>{items.length}</strong> {items.length === 1 ? "postulación" : "postulaciones"}</span>
            <span><strong>{withPlacement}</strong> con práctica asignada</span>
          </p>
          <div className="table-scroll" tabIndex={0} aria-label="Historial de postulaciones">
            <table className="data-table data-table--stack applications-table">
              <thead>
                <tr>
                  <th scope="col">Oportunidad</th>
                  <th scope="col">Postulación</th>
                  <th scope="col">Práctica</th>
                  <th scope="col">Elegibilidad</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((a) => (
                  <tr key={a.id}>
                    <td data-label="Oportunidad"><span className="cell-primary">{a.title}</span></td>
                    <td data-label="Postulación"><Badge>{a.state}</Badge></td>
                    <td data-label="Práctica">
                      {a.placement_id ? (
                        <div className="placement-cell">
                          <Badge>{a.placement_state}</Badge>
                          <div className="row-actions">
                            {(a.placement_state === "DOCUMENTATION_PENDING" || a.placement_state === "ACTIVE") && (
                              <button className="btn link" type="button" onClick={() => onNavigate("documents")}>Mis documentos</button>
                            )}
                            <button className="btn link" type="button" onClick={() => onNavigate("dossier")}>Ver expediente</button>
                          </div>
                        </div>
                      ) : <span className="muted">Sin práctica asignada</span>}
                    </td>
                    <td data-label="Elegibilidad" className="eligibility-cell"><EligibilitySummary value={a.eligibility_result} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
